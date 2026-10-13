from rest_framework import viewsets, permissions, filters, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
import logging
from django.db import transaction
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import Project, Task
from .serializers import ProjectSerializer, TaskSerializer, AddMemberSerializer
from .permissions import IsAssigneeOrProjectOwnerOrReadOnly, IsProjectManagerOrReadOnly
from accounts.permissions import can_manage_project
from erp_foundation.access import workspace_membership, can_admin_workspace, active_memberships
from notifications.emails import send_task_assigned_email
from notifications.services import send_async

class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated, IsProjectManagerOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        membership = workspace_membership(self.request)
        qs = Project.objects.filter(tenant=membership.tenant)
        if can_admin_workspace(membership):
            return qs
        return qs.filter(Q(owner=user) | Q(members=user)).distinct()

    @transaction.atomic
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user, tenant=workspace_membership(self.request).tenant)

    @action(detail=True, methods=['get'], url_path='board')
    def board(self, request, pk=None):
        """Return board metadata and tasks in one request to avoid the
        duplicated project/task round trips used by the Kanban screen."""
        project = self.get_object()
        tasks = project.tasks.select_related('assigned_to', 'parent').prefetch_related('linked_tasks').only(
            'id', 'project_id', 'title', 'description', 'status', 'priority',
            'due_date', 'assigned_to_id', 'updated_at', 'attachment', 'parent_id',
            'labels', 'story_points',
        ).order_by('status', 'due_date', 'title')
        return Response({
            'project': ProjectSerializer(project, context={'request': request}).data,
            'tasks': TaskSerializer(tasks, many=True).data,
        })

    @action(detail=True, methods=['post'], url_path='members')
    def add_member(self, request, pk=None):
        project = self.get_object()
        if not can_manage_project(request.user, project):
            raise PermissionDenied('You do not have permission to add members to this project.')

        serializer = AddMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_to_add = serializer.validated_data['email']
        if not active_memberships(user_to_add).filter(tenant_id=project.tenant_id).exists():
            raise PermissionDenied('Invite this person to the workspace before adding them to a project.')

        if user_to_add == project.owner:
            return Response({'detail': 'The owner is already on the project.'}, status=status.HTTP_400_BAD_REQUEST)

        project.members.add(user_to_add)
        return Response(ProjectSerializer(project, context={'request': request}).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['delete'], url_path=r'members/(?P<user_id>\d+)')
    def remove_member(self, request, pk=None, user_id=None):
        project = self.get_object()
        if not can_manage_project(request.user, project):
            raise PermissionDenied('You do not have permission to remove members from this project.')

        project.members.remove(user_id)
        return Response(ProjectSerializer(project, context={'request': request}).data, status=status.HTTP_200_OK)


class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated, IsAssigneeOrProjectOwnerOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'assigned_to', 'due_date', 'project']
    search_fields = ['title', 'description']
    ordering_fields = ['due_date', 'status']

    def get_queryset(self):
        user = self.request.user
        membership = workspace_membership(self.request)
        qs = Task.objects.filter(project__tenant=membership.tenant)
        if can_admin_workspace(membership):
            return qs
        return qs.filter(Q(project__owner=user) | Q(project__members=user)).distinct()

    @transaction.atomic
    def perform_create(self, serializer):
        project = serializer.validated_data.get('project')

        is_owner = project.owner == self.request.user
        is_member = project.members.filter(pk=self.request.user.pk).exists()
        membership = workspace_membership(self.request)
        if project.tenant_id != membership.tenant_id or not (is_owner or is_member or can_admin_workspace(membership)):
            raise PermissionDenied('You may only create tasks in projects you belong to.')
        from workspace_tools.quotas import enforce_upload_limit
        enforce_upload_limit(membership.tenant, serializer.validated_data.get('attachment'))
        task = serializer.save()
        self._notify_task_update(task)
        if task.assigned_to_id:
            send_async(send_task_assigned_email, task, assigned_by=self.request.user)

    @transaction.atomic
    def perform_update(self, serializer):
        previous_assignee_id = serializer.instance.assigned_to_id
        from workspace_tools.quotas import enforce_upload_limit
        enforce_upload_limit(serializer.instance.project.tenant, serializer.validated_data.get('attachment'))
        task = serializer.save()
        self._notify_task_update(task)
        if task.assigned_to_id and task.assigned_to_id != previous_assignee_id:
            send_async(send_task_assigned_email, task, assigned_by=self.request.user)

    def perform_destroy(self, instance):
        if not can_manage_project(self.request.user, instance.project):
            raise PermissionDenied("You do not have permission to delete tasks in this project.")
        instance.delete()

    def _notify_task_update(self, task):
        try:
            channel_layer = get_channel_layer()
            if channel_layer is None:
                return
            group_name = f"project_{task.project.id}"
            async_to_sync(channel_layer.group_send)(
                group_name,
                {
                    "type": "task_update",
                    "task_id": task.id,
                    "title": task.title,
                    "status": task.status,
                    "project_id": task.project.id,
                }
            )
        except Exception:
            logging.getLogger(__name__).exception('Task broadcast failed for task %s', task.pk)


class DashboardStatsView(APIView):
    """Aggregated numbers for the dashboard -- computed server-side so the
    frontend doesn't have to page through every project/task itself.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        membership = workspace_membership(request)
        projects = Project.objects.filter(tenant=membership.tenant)
        if not can_admin_workspace(membership):
            projects = projects.filter(Q(owner=user) | Q(members=user)).distinct()
        tasks = Task.objects.filter(project__in=projects)

        now = timezone.now()
        week_ago = now - timedelta(days=7)

        open_tasks = tasks.exclude(status=Task.DONE).count()
        completed_tasks = tasks.filter(status=Task.DONE).count()
        completed_last_week = tasks.filter(status=Task.DONE, completed_at__gte=week_ago).count()

        status_counts = {key: tasks.filter(status=key).count() for key, _label in Task.STATUS_CHOICES}

        daily_completed = []
        for i in range(6, -1, -1):
            day = (now - timedelta(days=i)).date()
            daily_completed.append({
                'label': day.strftime('%a'),
                'count': tasks.filter(status=Task.DONE, completed_at__date=day).count(),
            })

        overdue_qs = (
            tasks.exclude(status=Task.DONE)
            .exclude(due_date__isnull=True)
            .filter(due_date__lt=now)
            .select_related('project')
            .order_by('due_date')[:5]
        )
        overdue_tasks = [{
            'id': t.id,
            'title': t.title,
            'due_date': t.due_date,
            'project_name': t.project.name,
        } for t in overdue_qs]

        team_ids = set(projects.values_list('owner_id', flat=True))
        team_ids.update(tasks.exclude(assigned_to__isnull=True).values_list('assigned_to_id', flat=True))

        project_rows = list(
            projects.annotate(
                task_total=Count('tasks', distinct=True),
                done_count=Count('tasks', filter=Q(tasks__status=Task.DONE), distinct=True),
            ).values('id', 'name', 'task_total', 'done_count')[:6]
        )

        return Response({
            'open_tasks': open_tasks,
            'completed_tasks': completed_tasks,
            'completed_last_week': completed_last_week,
            'active_projects': projects.count(),
            'team_members': len(team_ids),
            'status_counts': status_counts,
            'daily_completed': daily_completed,
            'overdue_tasks': overdue_tasks,
            'projects': project_rows,
        })
