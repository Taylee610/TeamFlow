import csv
import io
from datetime import timedelta
from zoneinfo import ZoneInfo
from django.db import transaction
from django.db.models import Q, Count, Avg
from django.http import HttpResponse, FileResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets, permissions, serializers
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from erp_foundation.access import workspace_membership, can_admin_workspace
from accounts.permissions import can_view_project
from projects.models import Project, Task
from . import models, serializers as schemas
from .services import audit, enqueue


def csv_response(name, headings, rows):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headings)
    for row in rows:
        writer.writerow(["'" + str(v) if str(v).startswith(('=', '+', '-', '@', '\t', '\r')) else v for v in row])
    response = HttpResponse(output.getvalue(), content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{name}.csv"'
    response['Cache-Control'] = 'private, no-store'
    return response


class WorkspaceViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    model = None
    personal = False
    search_fields = ['name']
    record_limit = 500

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if request.method not in ('GET', 'HEAD', 'OPTIONS', 'DELETE'):
            from .billing import active_subscription
            active_subscription(workspace_membership(request).tenant)

    def get_queryset(self):
        membership = workspace_membership(self.request)
        qs = self.model.objects.filter(tenant=membership.tenant)
        if self.personal:
            qs = qs.filter(created_by=self.request.user)
        return qs

    def ensure_write(self, instance):
        if instance.created_by_id != self.request.user.pk and not can_admin_workspace(workspace_membership(self.request)):
            raise PermissionDenied('Only the owner or a workspace administrator can change this record.')

    def update(self, request, *args, **kwargs):
        self.ensure_write(self.get_object())
        return super().update(request, *args, **kwargs)

    @transaction.atomic
    def perform_create(self, serializer):
        membership = workspace_membership(self.request)
        # Serialize quota decisions per workspace, including simultaneous creates.
        type(membership.tenant).objects.select_for_update().get(pk=membership.tenant_id)
        from .billing import limit_for
        module = self.basename
        limit = limit_for(membership.tenant, module, self.record_limit)
        if self.model.objects.filter(tenant=membership.tenant).count() >= limit:
            raise serializers.ValidationError('This workspace has reached the record limit for this tool.')
        if isinstance(serializer, schemas.ApprovalSerializer):
            from .quotas import enforce_upload_limit
            enforce_upload_limit(membership.tenant, serializer.validated_data.get('file'))
        instance = serializer.save(tenant=membership.tenant, created_by=self.request.user)
        audit(instance, self.request.user, 'create')
        if isinstance(instance, models.ApprovalFile):
            self.notify_reviewer(instance)

    def notify_reviewer(self, instance):
        from django.conf import settings
        from .services import email_allowed
        if email_allowed(instance.client_user) and not models.NotificationPreference.objects.filter(user=instance.client_user, approval_alerts=False).exists():
            enqueue('email', {'to': instance.client_user.email, 'subject': f'Review requested: {instance.title}',
                             'guard_user': instance.client_user_id, 'guard_tenant': instance.tenant_id,
                             'body': f'Please review version {instance.version} in {instance.tenant.name}:\n{settings.FRONTEND_URL.rstrip("/")}/tools/approvals'}, f'approval:{instance.pk}:{instance.version}')

    @transaction.atomic
    def perform_update(self, serializer):
        from .billing import active_subscription
        active_subscription(workspace_membership(self.request).tenant)
        self.ensure_write(serializer.instance)
        instance = serializer.save()
        audit(instance, self.request.user, 'update')

    @transaction.atomic
    def perform_destroy(self, instance):
        self.ensure_write(instance)
        audit(instance, self.request.user, 'delete')
        instance.delete()


class MonitorViewSet(WorkspaceViewSet):
    model = models.Monitor
    serializer_class = schemas.MonitorSerializer
    record_limit = 30

    @action(detail=True, methods=['post'])
    def check(self, request, pk=None):
        monitor = self.get_object()
        self.ensure_write(monitor)
        if not monitor.enabled:
            raise serializers.ValidationError('Enable this monitor before checking it.')
        bucket = int(timezone.now().timestamp()) // 300
        job = enqueue('monitor', {'id': monitor.pk, 'url': monitor.url}, f'manual-monitor:{monitor.pk}:{bucket}')
        return Response({'detail': 'Check queued.', 'job_status': job.status}, status=202)

    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        monitor = self.get_object()
        checks = monitor.checks.filter(checked_at__gte=timezone.now() - timedelta(days=30))
        summary = checks.aggregate(total=Count('id'), up=Count('id', filter=Q(is_up=True)), latency=Avg('latency_ms', filter=Q(is_up=True)))
        return Response({'sample_count': summary['total'], 'uptime_percent': round(100 * summary['up'] / summary['total'], 2) if summary['total'] else None,
                         'average_latency_ms': summary['latency'], 'window_days': 30, 'measurement': 'successful checks / completed checks; missing checks are not counted',
                         'checks': list(checks.values('id', 'checked_at', 'is_up', 'status_code', 'latency_ms', 'error')[:100])})


class ClientViewSet(WorkspaceViewSet):
    model = models.Client
    serializer_class = schemas.ClientSerializer
    search_fields = ['name', 'email', 'company', 'notes']
    filterset_fields = ['stage']

    @action(detail=False, methods=['get'])
    def export(self, request):
        rows = self.filter_queryset(self.get_queryset()).values_list('name', 'email', 'phone', 'company', 'stage', 'notes')
        return csv_response('clients', ['Name', 'Email', 'Phone', 'Company', 'Stage', 'Notes'], rows)

    @action(detail=True, methods=['post'], url_path='create-project')
    @transaction.atomic
    def create_project(self, request, pk=None):
        client = self.get_object()
        self.ensure_write(client)
        name = serializers.CharField(max_length=100).run_validation(request.data.get('name'))
        if Project.objects.filter(tenant=client.tenant, owner=request.user, name=name).exists():
            raise serializers.ValidationError({'name': 'A project with this name already exists.'})
        project = Project.objects.create(tenant=client.tenant, owner=request.user, name=name, description=f'Client: {client.name}')
        client.projects.add(project)
        client.stage = 'active'
        client.save(update_fields=['stage', 'updated_at'])
        audit(client, request.user, 'convert', after={'project': project.pk})
        return Response({'project': project.pk}, status=201)


class LinkProfileViewSet(WorkspaceViewSet):
    model = models.LinkProfile
    serializer_class = schemas.LinkProfileSerializer
    search_fields = ['title', 'slug']


class PublicProfileView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'public_read'

    def get(self, request, slug):
        profile = get_object_or_404(models.LinkProfile, slug=slug, published=True, tenant__is_active=True)
        return Response({key: getattr(profile, key) for key in ('title', 'bio', 'theme', 'links', 'slug')})


class HabitViewSet(WorkspaceViewSet):
    model = models.Habit
    serializer_class = schemas.HabitSerializer
    personal = True

    @action(detail=True, methods=['get', 'post'])
    def logs(self, request, pk=None):
        habit = self.get_object()
        today = timezone.now().astimezone(ZoneInfo(habit.timezone)).date()
        if request.method == 'POST':
            day = serializers.DateField().run_validation(request.data.get('day', today.isoformat()))
            if day > today or day < today - timedelta(days=365):
                raise serializers.ValidationError('Log a day within the past year, up to today.')
            completed = serializers.BooleanField().run_validation(request.data.get('completed', True))
            log, _ = models.HabitLog.objects.update_or_create(habit=habit, day=day, defaults={'completed': completed})
            return Response({'day': log.day, 'completed': log.completed})
        days = set(habit.logs.filter(completed=True).values_list('day', flat=True))
        cursor = today if today in days else today - timedelta(days=1)
        streak = 0
        while cursor in days:
            streak += 1
            cursor -= timedelta(days=1)
        start = today - timedelta(days=29)
        completed_count = sum(start <= day <= today for day in days)
        return Response({'today': today, 'streak': streak, 'completed_last_30_days': completed_count, 'success_percent': round(completed_count / 30 * 100, 1),
                         'logs': list(habit.logs.filter(day__gte=start).order_by('day').values('day', 'completed'))})

    @action(detail=False, methods=['get'])
    def export(self, request):
        return csv_response('habits', ['Habit', 'Timezone', 'Day', 'Completed'], models.HabitLog.objects.filter(habit__in=self.get_queryset()).values_list('habit__name', 'habit__timezone', 'day', 'completed'))


class DeckViewSet(WorkspaceViewSet):
    model = models.Deck
    serializer_class = schemas.DeckSerializer

    def get_queryset(self):
        return super().get_queryset().filter(Q(created_by=self.request.user) | Q(shared=True)).annotate(card_count=Count('cards'))

    def ensure_write(self, instance):
        if instance.created_by_id != self.request.user.pk:
            raise PermissionDenied('Only the deck owner can change this deck.')

    @action(detail=True, methods=['get'])
    def study(self, request, pk=None):
        deck = self.get_object()
        now = timezone.now()
        due = deck.cards.exclude(progress__user=request.user, progress__due_at__gt=now).order_by('pk')[:100]
        return Response(schemas.FlashcardSerializer(due, many=True).data)


class FlashcardViewSet(WorkspaceViewSet):
    model = models.Flashcard
    serializer_class = schemas.FlashcardSerializer
    search_fields = ['question', 'answer']
    filterset_fields = ['deck']
    record_limit = 10000

    def get_queryset(self):
        return super().get_queryset().filter(Q(deck__created_by=self.request.user) | Q(deck__shared=True))

    def ensure_write(self, instance):
        if instance.deck.created_by_id != self.request.user.pk:
            raise PermissionDenied('Only the deck owner can change its cards.')

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def review(self, request, pk=None):
        card = self.get_object()
        rating = serializers.ChoiceField(choices=['hard', 'good', 'easy']).run_validation(request.data.get('rating'))
        key = serializers.UUIDField().run_validation(request.data.get('request_key'))
        progress, _ = models.CardProgress.objects.get_or_create(card=card, user=request.user)
        progress = models.CardProgress.objects.select_for_update().get(pk=progress.pk)
        _, created = models.StudyReview.objects.get_or_create(progress=progress, request_key=key, defaults={'rating': rating})
        if created:
            progress.interval_days = 1 if rating == 'hard' else min(365, max(2 if rating == 'good' else 4, progress.interval_days * (2 if rating == 'good' else 3)))
            progress.due_at = timezone.now() + timedelta(days=progress.interval_days)
            progress.last_reviewed_at = timezone.now()
            progress.reviews += 1
            progress.save()
        return Response({'due_at': progress.due_at, 'interval_days': progress.interval_days, 'reviews': progress.reviews})


class FormViewSet(WorkspaceViewSet):
    model = models.Form
    serializer_class = schemas.FormSerializer
    search_fields = ['title']

    @transaction.atomic
    def perform_update(self, serializer):
        current = models.Form.objects.select_for_update().get(pk=serializer.instance.pk)
        self.ensure_write(current)
        serializer.instance = current
        changed = any(key in serializer.validated_data and serializer.validated_data[key] != getattr(current, key) for key in ('fields', 'title', 'description'))
        instance = serializer.save(version=current.version + int(changed))
        audit(instance, self.request.user, 'update', after={'version': instance.version})

    @action(detail=True, methods=['get'])
    def responses(self, request, pk=None):
        form = self.get_object()
        page = self.paginate_queryset(form.responses.all())
        rows = [{'id': x.pk, 'version': x.version, 'schema': x.schema, 'answers': x.answers, 'submitted_at': x.submitted_at} for x in page]
        return self.get_paginated_response(rows)

    @action(detail=True, methods=['get'])
    def export(self, request, pk=None):
        form = self.get_object()
        responses = list(form.responses.all()[:10000])
        keys = list(dict.fromkeys(field['key'] for response in responses for field in response.schema))
        return csv_response('form-responses', ['Submitted', 'Version', *keys], [[r.submitted_at, r.version, *[r.answers.get(k, '') for k in keys]] for r in responses])


class PublicFormView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'public_submit'

    def get_throttles(self):
        self.throttle_scope = 'public_read' if self.request.method in ('GET', 'HEAD', 'OPTIONS') else 'public_submit'
        return super().get_throttles()

    def get(self, request, public_id):
        form = get_object_or_404(models.Form, public_id=public_id, published=True, tenant__is_active=True)
        return Response({'title': form.title, 'description': form.description, 'fields': form.fields, 'version': form.version})

    @transaction.atomic
    def post(self, request, public_id):
        form = get_object_or_404(models.Form.objects.select_for_update(), public_id=public_id, published=True, tenant__is_active=True)
        if request.data.get('website'):
            return Response({'detail': 'Thank you.'}, status=201)
        if request.data.get('version') != form.version:
            raise serializers.ValidationError('This form changed. Refresh it before submitting.')
        if form.responses.count() >= 10000:
            raise serializers.ValidationError('This form has reached its response limit.')
        answers = request.data.get('answers')
        if not isinstance(answers, dict) or set(answers) - {x['key'] for x in form.fields}:
            raise serializers.ValidationError('Invalid answers.')
        clean = {}
        errors = {}
        for field in form.fields:
            value = answers.get(field['key'], '')
            validator = serializers.EmailField if field['type'] == 'email' else serializers.CharField
            try:
                clean[field['key']] = validator(allow_blank=not field['required'], max_length=5000).run_validation(value)
                if field['type'] in ('choice', 'dropdown') and clean[field['key']] and clean[field['key']] not in field['options']:
                    errors[field['key']] = 'Choose one of the listed options.'
            except serializers.ValidationError as exc:
                errors[field['key']] = exc.detail
        if errors:
            raise serializers.ValidationError(errors)
        models.FormResponse.objects.create(form=form, version=form.version, schema=form.fields, answers=clean)
        return Response({'detail': 'Response received.'}, status=201)


class FeedbackWidgetViewSet(WorkspaceViewSet):
    model = models.FeedbackWidget
    serializer_class = schemas.FeedbackWidgetSerializer


class FeedbackViewSet(viewsets.ModelViewSet):
    serializer_class = schemas.FeedbackSerializer
    http_method_names = ['get', 'patch', 'post', 'head', 'options']
    search_fields = ['message', 'email']
    filterset_fields = ['status', 'widget']

    def get_queryset(self):
        return models.Feedback.objects.filter(widget__tenant=workspace_membership(self.request).tenant)

    def create(self, request, *args, **kwargs):
        raise PermissionDenied('Submit feedback through a registered public widget.')

    @action(detail=True, methods=['post'], url_path='create-task')
    @transaction.atomic
    def create_task(self, request, pk=None):
        feedback = self.get_object()
        feedback = models.Feedback.objects.select_for_update().get(pk=feedback.pk)
        project_id = serializers.IntegerField(min_value=1).run_validation(request.data.get('project'))
        project = get_object_or_404(Project, pk=project_id, tenant=feedback.widget.tenant)
        if not can_view_project(request.user, project):
            raise PermissionDenied('Choose a project you can access.')
        if not feedback.task_id:
            feedback.task = Task.objects.create(project=project, title=feedback.message[:100], description=feedback.message)
            feedback.status = 'read'
            feedback.save()
            audit(feedback.widget, request.user, 'feedback.convert', after={'task': feedback.task_id})
        return Response({'task': feedback.task_id, 'project': feedback.task.project_id})


class PublicFeedbackView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'public_submit'

    def get_throttles(self):
        self.throttle_scope = 'public_read' if self.request.method in ('GET', 'HEAD', 'OPTIONS') else 'public_submit'
        return super().get_throttles()

    def widget(self, request, public_id):
        widget = get_object_or_404(models.FeedbackWidget, public_id=public_id, enabled=True, tenant__is_active=True)
        origin = request.headers.get('Origin', '').lower()
        if origin not in widget.allowed_origins:
            raise PermissionDenied('This website is not registered for this widget.')
        return widget, origin

    def cors(self, response, origin):
        response['Access-Control-Allow-Origin'] = origin
        response['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type'
        response['Vary'] = 'Origin'
        response['Cache-Control'] = 'no-store'
        return response

    def options(self, request, public_id):
        _, origin = self.widget(request, public_id)
        return self.cors(Response(status=204), origin)

    def get(self, request, public_id):
        widget, origin = self.widget(request, public_id)
        return self.cors(Response({'label': widget.label}), origin)

    @transaction.atomic
    def post(self, request, public_id):
        widget, origin = self.widget(request, public_id)
        widget = models.FeedbackWidget.objects.select_for_update().get(pk=widget.pk)
        serializer = schemas.FeedbackInput(data=request.data)
        if not serializer.is_valid():
            return self.cors(Response(serializer.errors, status=400), origin)
        values = serializer.validated_data
        if not values.pop('website', ''):
            if widget.feedback.count() >= 10000:
                return self.cors(Response({'detail': 'Feedback limit reached.'}, status=400), origin)
            models.Feedback.objects.create(widget=widget, **values)
        return self.cors(Response({'detail': 'Thank you for your feedback.'}, status=201), origin)


class WikiViewSet(WorkspaceViewSet):
    model = models.WikiPage
    serializer_class = schemas.WikiSerializer
    search_fields = ['title', 'body']

    @transaction.atomic
    def perform_update(self, serializer):
        self.ensure_write(serializer.instance)
        models.WikiRevision.objects.create(page=serializer.instance, title=serializer.instance.title, body=serializer.instance.body, actor=self.request.user)
        super().perform_update(serializer)

    @action(detail=True, methods=['get'])
    def revisions(self, request, pk=None):
        return Response(list(self.get_object().revisions.order_by('-id').values('id', 'title', 'body', 'actor_id', 'created_at')[:50]))


class ApprovalViewSet(WorkspaceViewSet):
    model = models.ApprovalFile
    serializer_class = schemas.ApprovalSerializer
    search_fields = ['title']

    def get_queryset(self):
        qs = super().get_queryset()
        if can_admin_workspace(workspace_membership(self.request)):
            return qs
        return qs.filter(Q(created_by=self.request.user) | Q(client_user=self.request.user))

    @transaction.atomic
    def perform_update(self, serializer):
        current = models.ApprovalFile.objects.select_for_update().get(pk=serializer.instance.pk)
        self.ensure_write(current)
        serializer.instance = current
        if 'file' in serializer.validated_data or 'client_user' in serializer.validated_data:
            from .quotas import enforce_upload_limit
            enforce_upload_limit(current.tenant, serializer.validated_data.get('file'))
            models.ApprovalVersion.objects.get_or_create(approval=current, version=current.version,
                defaults={'title': current.title, 'file': current.file.name, 'status': current.status, 'comment': current.comment,
                          'approved_at': current.approved_at, 'approved_by': current.approved_by})
            serializer.save(version=current.version + 1, status='pending', approved_at=None, approved_by=None, comment='')
            self.notify_reviewer(serializer.instance)
        super().perform_update(serializer)

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def decide(self, request, pk=None):
        instance = self.get_object()
        instance = models.ApprovalFile.objects.select_for_update().get(pk=instance.pk)
        if instance.client_user_id != request.user.pk:
            raise PermissionDenied('Only the assigned client reviewer can decide.')
        version = serializers.IntegerField(min_value=1).run_validation(request.data.get('version'))
        if version != instance.version or instance.status != 'pending':
            raise serializers.ValidationError('This version is no longer pending. Refresh the page.')
        choice = serializers.ChoiceField(choices=['approved', 'revision']).run_validation(request.data.get('status'))
        instance.comment = serializers.CharField(max_length=5000, allow_blank=True).run_validation(request.data.get('comment', ''))
        instance.status = choice
        instance.approved_by = request.user if choice == 'approved' else None
        instance.approved_at = timezone.now() if choice == 'approved' else None
        instance.save()
        audit(instance, request.user, choice, after={'version': instance.version})
        from .services import email_allowed
        from django.conf import settings
        if email_allowed(instance.created_by) and not models.NotificationPreference.objects.filter(user=instance.created_by, approval_alerts=False).exists():
            enqueue('email', {'to': instance.created_by.email, 'guard_user': instance.created_by_id, 'guard_tenant': instance.tenant_id,
                             'subject': f'{instance.title}: {choice}', 'body': f'Version {instance.version} was reviewed in {instance.tenant.name}.\nDecision: {choice}\n{instance.comment}\n{settings.FRONTEND_URL.rstrip("/")}/tools/approvals'},
                    f'approval-decision:{instance.pk}:{instance.version}')
        return Response(self.get_serializer(instance).data)

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        from pathlib import PurePosixPath
        instance = self.get_object()
        response = FileResponse(instance.file.open('rb'), as_attachment=True, filename=PurePosixPath(instance.file.name).name)
        response['Cache-Control'] = 'private, no-store'
        return response

    @action(detail=True, methods=['get'])
    def versions(self, request, pk=None):
        approval = self.get_object()
        return Response(list(approval.versions.order_by('-version').values('version', 'title', 'status', 'comment', 'approved_at', 'approved_by_id')))

    @action(detail=True, methods=['get'], url_path=r'versions/(?P<version>\d+)/download')
    def download_version(self, request, pk=None, version=None):
        from pathlib import PurePosixPath
        approval = self.get_object()
        record = get_object_or_404(approval.versions, version=version)
        response = FileResponse(record.file.open('rb'), as_attachment=True, filename=PurePosixPath(record.file.name).name)
        response['Cache-Control'] = 'private, no-store'
        return response


class TimeLogViewSet(WorkspaceViewSet):
    model = models.TimeLog
    serializer_class = schemas.TimeLogSerializer
    personal = True
    search_fields = ['note']


class PreferencesView(APIView):
    def get(self, request):
        prefs, _ = models.NotificationPreference.objects.get_or_create(user=request.user)
        return Response({field: getattr(prefs, field) for field in ('email_notifications', 'period_reminders', 'approval_alerts')})

    def patch(self, request):
        prefs, _ = models.NotificationPreference.objects.get_or_create(user=request.user)
        for field in ('email_notifications', 'period_reminders', 'approval_alerts'):
            if field in request.data:
                setattr(prefs, field, serializers.BooleanField().run_validation(request.data[field]))
        prefs.save()
        return self.get(request)


class JobsView(APIView):
    def get(self, request):
        membership = workspace_membership(request)
        if not can_admin_workspace(membership):
            raise PermissionDenied('Workspace administrators only.')
        ids = list(models.Monitor.objects.filter(tenant=membership.tenant).values_list('pk', flat=True))
        jobs = models.Job.objects.filter(kind='monitor', payload__id__in=ids).order_by('-id')[:50]
        return Response(list(jobs.values('id', 'status', 'attempts', 'last_error', 'created_at')))


def widget_script(request):
    from pathlib import Path
    script = Path(__file__).parent / 'static' / 'tools' / 'widget.js'
    response = HttpResponse(script.read_text(encoding='utf-8'), content_type='application/javascript')
    response['Cache-Control'] = 'public, max-age=3600'
    return response
