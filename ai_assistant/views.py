import json
import logging

import anthropic
from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, serializers
from django.db import transaction
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from projects.models import Project, Task
from accounts.permissions import can_view_project
from erp_foundation.access import workspace_membership
from .client import get_client
from .serializers import TaskAssistRequestSerializer
from workspace_tools.quotas import reserve_ai_request

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
    return can_view_project(user, project)


class TaskAssistView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'ai'

    def post(self, request):
        serializer = TaskAssistRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        prompt = serializer.validated_data['prompt']
        project = serializer.validated_data.get('project')

        if project and (project.tenant_id != workspace_membership(request).tenant_id or not _can_view_project(request.user, project)):
            raise PermissionDenied('You do not have access to that project.')
        reserve_ai_request(workspace_membership(request).tenant)
        if settings.TAYLEE_ENGINE == 'local_ml':
            from .ml import plan
            return Response(plan(prompt))
        client = get_client()
        if client is None:
            return Response({'detail': 'AI features are not set up yet.'}, status=503)

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
        from .serializers import TaskAssistResponseSerializer
        try:
            data = json.loads(text)
        except (TypeError, ValueError):
            return Response({'detail': 'AI returned an invalid suggestion. Please retry.'}, status=502)
        output = TaskAssistResponseSerializer(data=data)
        if not output.is_valid():
            return Response({'detail': 'AI returned incomplete suggestions. Please retry.'}, status=502)
        return Response(output.validated_data)


class ProjectSummaryView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'ai'

    def get(self, request, project_id):
        project = get_object_or_404(Project, pk=project_id)
        if project.tenant_id != workspace_membership(request).tenant_id or not _can_view_project(request.user, project):
            raise PermissionDenied('You do not have access to that project.')
        reserve_ai_request(workspace_membership(request).tenant)
        if settings.TAYLEE_ENGINE == 'local_ml':
            from django.db.models import Q
            from erp_foundation.access import can_admin_workspace
            from .ml import project_insights
            membership = workspace_membership(request)
            accessible = Project.objects.filter(tenant=membership.tenant)
            if not can_admin_workspace(membership):
                accessible = accessible.filter(Q(owner=request.user) | Q(members=request.user)).distinct()
            return Response(project_insights(project, accessible))
        client = get_client()
        if client is None:
            return Response({'detail': 'AI features are not set up yet.'}, status=503)

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


class SavePlanView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        import hashlib
        from .serializers import TaskAssistResponseSerializer
        project_id = serializers.IntegerField(min_value=1).run_validation(request.data.get('project'))
        project = get_object_or_404(Project.objects.select_for_update(), pk=project_id, tenant=workspace_membership(request).tenant)
        if not can_view_project(request.user, project):
            raise PermissionDenied('You do not have access to that project.')
        key = str(serializers.UUIDField().run_validation(request.data.get('request_key')))
        title = serializers.CharField(max_length=100).run_validation(request.data.get('title'))
        output = TaskAssistResponseSerializer(data=request.data.get('plan'))
        output.is_valid(raise_exception=True)
        data = output.validated_data
        if len(data['subtasks']) > 20 or any(len(x) > 100 for x in data['subtasks']) or len(data['description']) > 10000:
            raise serializers.ValidationError('Use up to 20 subtasks, with titles up to 100 characters.')
        due = serializers.DateField(allow_null=True).run_validation(data['due_date'])
        fingerprint = hashlib.sha256(json.dumps({'title': title, 'plan': data}, sort_keys=True).encode()).hexdigest()
        existing = project.tasks.filter(labels__0='taylee-plan', labels__1=key).first()
        if existing:
            if existing.labels[2] != fingerprint:
                return Response({'detail': 'This save request was already used for a different plan.'}, status=409)
            return Response({'id': existing.pk, 'project': project.pk}, status=200)
        from datetime import datetime, time
        from django.utils import timezone
        deadline = timezone.make_aware(datetime.combine(due, time(17))) if due else None
        task = Task.objects.create(project=project, title=title, description=data['description'], priority=data['priority'], due_date=deadline, labels=['taylee-plan', key, fingerprint])
        for title in data['subtasks']:
            Task.objects.create(project=project, parent=task, title=title, priority=data['priority'])
        from erp_foundation.models import AuditLog
        AuditLog.objects.create(tenant=project.tenant, actor=request.user, action='ai.plan.save', object_type='projects.Task', object_id=str(task.pk), after={'subtasks': len(data['subtasks'])})
        return Response({'id': task.pk, 'project': project.pk}, status=201)
