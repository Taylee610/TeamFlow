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
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import Project, Task
from .serializers import ProjectSerializer, TaskSerializer, AddMemberSerializer
from .permissions import IsAssigneeOrProjectOwnerOrReadOnly, IsProjectManagerOrReadOnly
from accounts.permissions import can_manage_project
from notifications.emails import send_task_assigned_email
from notifications.services import send_async

class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated, IsProjectManagerOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        if user.is_admin:
            return Project.objects.all()
        return Project.objects.filter(Q(owner=user) | Q(members=user)).distinct()

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=['post'], url_path='members')
    def add_member(self, request, pk=None):
        project = self.get_object()
        if not can_manage_project(request.user, project):
            raise PermissionDenied('You do not have permission to add members to this project.')

        serializer = AddMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_to_add = serializer.validated_data['email']

        if user_to_add == project.owner:
            return Response({'detail': 'The owner is already on the project.'}, status=status.HTTP_400_BAD_REQUEST)

        project.members.add(user_to_add)
        return Response(ProjectSerializer(project).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['delete'], url_path=r'members/(?P<user_id>\d+)')
    def remove_member(self, request, pk=None, user_id=None):
        project = self.get_object()
        if not can_manage_project(request.user, project):
            raise PermissionDenied('You do not have permission to remove members from this project.')

        project.members.remove(user_id)
        return Response(ProjectSerializer(project).data, status=status.HTTP_200_OK)


class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated, IsAssigneeOrProjectOwnerOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'assigned_to', 'due_date', 'project']
    search_fields = ['title', 'description']
    ordering_fields = ['due_date', 'status']

    def get_queryset(self):
        user = self.request.user
        if user.is_admin:
            return Task.objects.all()
        qs_owner = Task.objects.filter(project__owner=user)
        qs_member = Task.objects.filter(project__members=user)
        qs_assigned = Task.objects.filter(assigned_to=user)
        return (qs_owner | qs_member | qs_assigned).distinct()

    def perform_create(self, serializer):
        project = serializer.validated_data.get('project')

        is_owner = project.owner == self.request.user
        is_member = project.members.filter(pk=self.request.user.pk).exists()
        if not (is_owner or is_member or self.request.user.is_admin):
            raise PermissionDenied('You may only create tasks in projects you belong to.')
        task = serializer.save()
        self._notify_task_update(task)
        if task.assigned_to_id:
            send_async(send_task_assigned_email, task, assigned_by=self.request.user)

    def perform_update(self, serializer):
        previous_assignee_id = serializer.instance.assigned_to_id
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
            pass


class DashboardStatsView(APIView):
    """Aggregated numbers for the dashboard -- computed server-side so the
    frontend doesn't have to page through every project/task itself.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        projects = Project.objects.filter(owner=user)
        tasks = (Task.objects.filter(project__owner=user) | Task.objects.filter(assigned_to=user)).distinct()

        now = timezone.now()
        week_ago = now - timedelta(days=7)

        open_tasks = tasks.exclude(status=Task.DONE).count()
        completed_tasks = tasks.filter(status=Task.DONE).count()
        completed_last_week = tasks.filter(status=Task.DONE, updated_at__gte=week_ago).count()

        status_counts = {key: tasks.filter(status=key).count() for key, _label in Task.STATUS_CHOICES}

        daily_completed = []
        for i in range(6, -1, -1):
            day = (now - timedelta(days=i)).date()
            daily_completed.append({
                'label': day.strftime('%a'),
                'count': tasks.filter(status=Task.DONE, updated_at__date=day).count(),
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