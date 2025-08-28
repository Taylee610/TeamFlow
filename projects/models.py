from django.db import models
from django.conf import settings
from django.urls import reverse

class Project(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='projects')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
            return self.name
        
    def get_absolute_url(self):
            return reverse("project_detail", args={"pk": self.pk})
        
class Task(models.Model):
            TODO = 1
            IN_PROGRESS = 2
            DONE = 3
            STATUS_CHOICES = [(TODO,'todo'), (IN_PROGRESS,'in_progress'), (DONE,'done')]

            project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='tasks')
            title = models.CharField(max_length=100)
            description = models.TextField(blank=True)
            status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=TODO)
            Assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tasks')
            created_at = models.DateTimeField(auto_now_add=True)
            updated_at = models.DateTimeField(auto_now=True)

class Meta:
                ordering = ('status','due_date','title')
                unique_together = ('owner', 'name')

                def __str__(self):
                    return f"{self.title}({self.project.name})"

                def get_absolute_url(self):
                    return reverse("project_detail", args=[self.project_id])
                    
        
