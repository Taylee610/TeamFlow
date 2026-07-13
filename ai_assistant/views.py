import json
import logging

import anthropic
from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from projects.models import Project, Task
from .client import get_client
from .serializers import TaskAssistRequestSerializer

logger = logging.getLogger(__name__)

TASK_ASSIST_SCHEMA = {
    'type': 'object',
    'properties': {
        'description': {'type': 'string', 'description': 'A clear task description, 1-3 sentences.'},
        'subtasks': {'type': 'array', 'items': {'type': 'string'}, 'description': 'A short checklist of concrete subtasks.'},
        'priority': {'type': 'string', 'enum': ['low', 'medium', 'high']},
        'due_date': {
            'anyOf': [{'type': 'string', 'description': 'ISO 8601 date, e.g. 2025-09-01'}, {'type': 'null'}],
        },
    },
    'required': ['description', 'subtasks', 'priority', 'due_date'],
    'additionalProperties': False,
}


def _can_view_project(user, project):
    return (
        project.owner_id == user.id
        or project.members.filter(pk=user.pk).exists()
        or user.is_admin
    )


class TaskAssistView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'ai'

    def post(self, request):
        client = get_client()
        if client is None:
            return Response({'detail': 'AI features are not set up yet.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        serializer = TaskAssistRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        prompt = serializer.validated_data['prompt']
        project = serializer.validated_data.get('project')

        if project and not _can_view_project(request.user, project):
            raise PermissionDenied('You do not have access to that project.')

        existing_titles = []
        if project:
            existing_titles = list(project.tasks.values_list('title', flat=True)[:20])

        context_note = ''
        if existing_titles:
            context_note = (
                '\n\nExisting task titles in this project (avoid exact duplicates):\n- '
                + '\n- '.join(existing_titles)
            )

        try:
            message = client.messages.create(
                model=settings.ANTHROPIC_MODEL,
                max_tokens=1024,
                system=(
                    'You help a project manager turn a short prompt into a well-formed task. '
                    'Respond with a clear description, a short checklist of concrete subtasks, '
                    'a suggested priority, and a suggested due date (ISO 8601 date, or null if '
                    'none makes sense).'
                ),
                messages=[{'role': 'user', 'content': f'{prompt}{context_note}'}],
                output_config={'format': {'type': 'json_schema', 'schema': TASK_ASSIST_SCHEMA}},
            )
        except anthropic.RateLimitError:
            return Response({'detail': 'AI service is rate limited, try again shortly.'}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        except anthropic.APIError:
            logger.exception('Anthropic task-assist request failed')
            return Response({'detail': 'Could not generate suggestions.'}, status=status.HTTP_502_BAD_GATEWAY)

        text = next((block.text for block in message.content if block.type == 'text'), '{}')
        data = json.loads(text)
        return Response(data)


class ProjectSummaryView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'ai'

    def get(self, request, project_id):
        client = get_client()
        if client is None:
            return Response({'detail': 'AI features are not set up yet.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        project = get_object_or_404(Project, pk=project_id)
        if not _can_view_project(request.user, project):
            raise PermissionDenied('You do not have access to that project.')

        tasks = project.tasks.all()
        status_counts = {key: tasks.filter(status=key).count() for key, _label in Task.STATUS_CHOICES}
        overdue = list(
            tasks.exclude(status=Task.DONE)
            .filter(due_date__isnull=False)
            .order_by('due_date')
            .values_list('title', flat=True)[:10]
        )

        context = (
            f'Project: {project.name}\n'
            f'Description: {project.description or "(none)"}\n'
            f'Task status counts: {status_counts}\n'
            f'Overdue or upcoming tasks (title): {overdue}\n'
        )

        try:
            message = client.messages.create(
                model=settings.ANTHROPIC_MODEL,
                max_tokens=1024,
                system=(
                    'You write a short, plain-English status digest for a project manager based on '
                    'the task data given. Cover overall progress, notable blockers or overdue items, '
                    'and one suggested next step. Keep it under 200 words. Plain text, no markdown headers.'
                ),
                messages=[{'role': 'user', 'content': context}],
            )
        except anthropic.RateLimitError:
            return Response({'detail': 'AI service is rate limited, try again shortly.'}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        except anthropic.APIError:
            logger.exception('Anthropic project-summary request failed')
            return Response({'detail': 'Could not generate a summary.'}, status=status.HTTP_502_BAD_GATEWAY)

        summary = next((block.text for block in message.content if block.type == 'text'), '')
        return Response({'summary': summary})
