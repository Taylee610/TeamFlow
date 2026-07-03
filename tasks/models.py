from django.db import models
from django.contrib.auth.models import User

class Task(models.Model):
    PRIORITY = (
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
    )

    STATUS = (
        ('TODO', 'To Do'),
        ('IN_PROGRESS', 'In Progress'),
        ('DONE', 'Done'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    priority = models.CharField(max_length=10, choices=PRIORITY, default='MEDIUM')
    status = models.CharField(max_length=15, choices=STATUS, default='TODO')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title