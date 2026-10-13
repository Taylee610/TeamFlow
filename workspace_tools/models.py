import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone


class WorkspaceRecord(models.Model):
    tenant = models.ForeignKey('erp_foundation.Tenant', on_delete=models.CASCADE)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ['-created_at', '-id']


class Job(models.Model):
    kind = models.CharField(max_length=40)
    payload = models.JSONField(default=dict)
    dedup_key = models.CharField(max_length=180, unique=True)
    status = models.CharField(max_length=12, default='pending')
    attempts = models.PositiveSmallIntegerField(default=0)
    available_at = models.DateTimeField(default=timezone.now)
    locked_until = models.DateTimeField(null=True)
    lease = models.UUIDField(null=True)
    last_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['status', 'available_at'])]


class NotificationPreference(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    email_notifications = models.BooleanField(default=True)
    period_reminders = models.BooleanField(default=True)
    approval_alerts = models.BooleanField(default=True)


class Monitor(WorkspaceRecord):
    name = models.CharField(max_length=180)
    url = models.URLField(max_length=1000)
    interval_minutes = models.PositiveIntegerField(default=5)
    enabled = models.BooleanField(default=True)
    state = models.CharField(max_length=12, default='unknown')
    next_check_at = models.DateTimeField(default=timezone.now)
    last_checked_at = models.DateTimeField(null=True)
    incident_started_at = models.DateTimeField(null=True)


class MonitorCheck(models.Model):
    monitor = models.ForeignKey(Monitor, on_delete=models.CASCADE, related_name='checks')
    checked_at = models.DateTimeField(default=timezone.now)
    is_up = models.BooleanField()
    status_code = models.PositiveIntegerField(null=True)
    latency_ms = models.PositiveIntegerField(default=0)
    error = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ['-checked_at', '-id']


class Client(WorkspaceRecord):
    name = models.CharField(max_length=180)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    company = models.CharField(max_length=180, blank=True)
    stage = models.CharField(max_length=20, choices=[(x, x.title()) for x in ['lead', 'active', 'completed', 'archived']], default='lead')
    notes = models.TextField(blank=True)
    projects = models.ManyToManyField('projects.Project', blank=True)


class LinkProfile(WorkspaceRecord):
    slug = models.SlugField(max_length=60, unique=True)
    title = models.CharField(max_length=180)
    bio = models.TextField(blank=True)
    theme = models.CharField(max_length=20, choices=[(x, x.title()) for x in ['indigo', 'emerald', 'slate']], default='indigo')
    links = models.JSONField(default=list)
    published = models.BooleanField(default=False)


class Habit(WorkspaceRecord):
    name = models.CharField(max_length=180)
    timezone = models.CharField(max_length=80, default='Africa/Harare')
    archived = models.BooleanField(default=False)


class HabitLog(models.Model):
    habit = models.ForeignKey(Habit, on_delete=models.CASCADE, related_name='logs')
    day = models.DateField()
    completed = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['habit', 'day'], name='unique_habit_day')]


class Deck(WorkspaceRecord):
    name = models.CharField(max_length=180)
    shared = models.BooleanField(default=False)


class Flashcard(WorkspaceRecord):
    deck = models.ForeignKey(Deck, on_delete=models.CASCADE, related_name='cards')
    question = models.TextField()
    answer = models.TextField()


class CardProgress(models.Model):
    card = models.ForeignKey(Flashcard, on_delete=models.CASCADE, related_name='progress')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    due_at = models.DateTimeField(default=timezone.now)
    interval_days = models.PositiveIntegerField(default=0)
    reviews = models.PositiveIntegerField(default=0)
    last_reviewed_at = models.DateTimeField(null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['card', 'user'], name='unique_card_progress')]


class StudyReview(models.Model):
    progress = models.ForeignKey(CardProgress, on_delete=models.CASCADE)
    request_key = models.UUIDField(default=uuid.uuid4)
    rating = models.CharField(max_length=10)
    reviewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['progress', 'request_key'], name='unique_study_review')]


class Form(WorkspaceRecord):
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    fields = models.JSONField(default=list)
    published = models.BooleanField(default=False)
    version = models.PositiveIntegerField(default=1)


class FormResponse(models.Model):
    form = models.ForeignKey(Form, on_delete=models.CASCADE, related_name='responses')
    version = models.PositiveIntegerField()
    schema = models.JSONField()
    answers = models.JSONField()
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-submitted_at', '-id']


class FeedbackWidget(WorkspaceRecord):
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=180)
    allowed_origins = models.JSONField(default=list)
    label = models.CharField(max_length=80, default='Leave feedback')
    enabled = models.BooleanField(default=True)


class Feedback(models.Model):
    widget = models.ForeignKey(FeedbackWidget, on_delete=models.CASCADE, related_name='feedback')
    message = models.TextField()
    email = models.EmailField(blank=True)
    page_url = models.URLField(max_length=1000, blank=True)
    status = models.CharField(max_length=12, choices=[(x, x.title()) for x in ['new', 'read', 'archived']], default='new')
    task = models.ForeignKey('projects.Task', null=True, on_delete=models.SET_NULL)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-submitted_at', '-id']


class WikiPage(WorkspaceRecord):
    title = models.CharField(max_length=180)
    body = models.TextField(blank=True)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.PROTECT)


class WikiRevision(models.Model):
    page = models.ForeignKey(WikiPage, on_delete=models.CASCADE, related_name='revisions')
    title = models.CharField(max_length=180)
    body = models.TextField()
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)


class ApprovalFile(WorkspaceRecord):
    client = models.ForeignKey(Client, on_delete=models.PROTECT)
    title = models.CharField(max_length=180)
    file = models.FileField(upload_to='approvals/%Y/%m/')
    version = models.PositiveIntegerField(default=1)
    client_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='approval_files')
    status = models.CharField(max_length=12, default='pending')
    approved_at = models.DateTimeField(null=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT, related_name='approved_files')
    comment = models.TextField(blank=True)


class TimeLog(WorkspaceRecord):
    task = models.ForeignKey('projects.Task', on_delete=models.PROTECT)
    work_date = models.DateField()
    hours = models.DecimalField(max_digits=5, decimal_places=2)
    note = models.TextField(blank=True)
    billable = models.BooleanField(default=False)


class BillingPayment(WorkspaceRecord):
    reference = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    request_key = models.UUIDField(unique=True)
    plan = models.ForeignKey('erp_operations.SaaSPlan', on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    method = models.CharField(max_length=12, default='paynow')
    status = models.CharField(max_length=20, default='queued')
    poll_url = models.URLField(max_length=1000, blank=True)
    checkout_url = models.URLField(max_length=1000, blank=True)
    instructions = models.TextField(blank=True)
    provider_reference = models.CharField(max_length=100, blank=True)
    granted_at = models.DateTimeField(null=True)
    period_end = models.DateTimeField(null=True)


class BillingEvent(models.Model):
    payment = models.ForeignKey(BillingPayment, on_delete=models.CASCADE)
    digest = models.CharField(max_length=128, unique=True)
    status = models.CharField(max_length=40)
    created_at = models.DateTimeField(auto_now_add=True)


class UsageCounter(models.Model):
    tenant = models.ForeignKey('erp_foundation.Tenant', on_delete=models.CASCADE)
    module = models.CharField(max_length=40)
    period = models.CharField(max_length=10)
    count = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['tenant', 'module', 'period'], name='unique_workspace_usage_period')]


class ApprovalVersion(models.Model):
    approval = models.ForeignKey(ApprovalFile, on_delete=models.CASCADE, related_name='versions')
    version = models.PositiveIntegerField()
    title = models.CharField(max_length=180)
    file = models.FileField(upload_to='approvals/%Y/%m/')
    status = models.CharField(max_length=12)
    comment = models.TextField(blank=True)
    approved_at = models.DateTimeField(null=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT)
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['approval', 'version'], name='unique_approval_version')]
