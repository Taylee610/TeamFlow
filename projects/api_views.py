from rest_framework import viewsets, permissions, filters, status
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import Project, Task
from .serializers import ProjectSerializer, TaskSerializer
from .permissions import IsAssigneeOrProjectOwnerOrReadOnly

class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Project.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated, IsAssigneeOrProjectOwnerOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'assigned_to', 'due_date']
    search_fields = ['title', 'description']
    ordering_fields = ['due_date', 'status']

    def get_queryset(self):
        
        qs_owner = Task.objects.filter(project__owner=self.request.user)
        qs_assigned = Task.objects.filter(assigned_to=self.request.user)
        return (qs_owner | qs_assigned).distinct()

    def perform_create(self, serializer):
        project = serializer.validated_data.get('project')
        
        if project.owner != self.request.user:
            return Response({'detail': 'You may only create tasks in your own projects.'}, status=status.HTTP_403_FORBIDDEN)
        task = serializer.save()
        self._notify_task_update(task)

    def perform_update(self, serializer):
        task = serializer.save()
        self._notify_task_update(task)

    def perform_destroy(self, instance):
        
        if instance.project.owner != self.request.user:
            raise permissions.PermissionDenied("Only project owner can delete tasks.")
        instance.delete()
        
    
    def _notify_task_update(self, task):
        channel_layer = get_channel_layer()
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
