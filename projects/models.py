from django.db import models
from django.conf import settings
from django.urls import reverse

class Project(models.Model):
    # Unmapped legacy records are quarantined from customer APIs.
    tenant = models.ForeignKey('erp_foundation.Tenant', on_delete=models.PROTECT, null=True, blank=True, related_name='projects')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='projects')
    created_at = models.DateTimeField(auto_now_add=True)
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='member_projects', blank=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('owner', 'name')

    def __str__(self):
            return self.name
        
    def get_absolute_url(self):
        return reverse("project-detail", kwargs={"pk": self.pk})

        
class Task(models.Model):
    TODO = 'todo'
    IN_PROGRESS = 'in_progress'
    DRAFTING = 'drafting'
    IN_REVIEW = 'in_review'
    DONE = 'done'
    STATUS_CHOICES = [
        (TODO, 'To do'),
        (DRAFTING, 'Drafting'),
        (IN_REVIEW, 'In review'),
        (DONE, 'Done'),
        (IN_PROGRESS, 'In progress (legacy)'),
    ]

    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    PRIORITY_CHOICES = [(LOW, 'low'), (MEDIUM, 'medium'), (HIGH, 'high')]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=TODO)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default=MEDIUM)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tasks')
    due_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    attachment = models.FileField(upload_to='task_files/', blank=True, null=True)
    reminder_sent_at = models.DateTimeField(null=True, blank=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='child_tasks')
    linked_tasks = models.ManyToManyField('self', symmetrical=True, blank=True)
    labels = models.JSONField(default=list, blank=True)
    story_points = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        ordering = ('status','due_date','title')

    def __str__(self):
        return f"{self.title}({self.project.name})"

    def get_absolute_url(self):
        return reverse("project-detail", args=[self.project_id])
