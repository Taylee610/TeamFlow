from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import Project, Task

User = get_user_model()

class ProjectTaskTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='test@example.com',password= 'pass123')
        self.client.login(email='test@example.com',password= 'pass123')

    def test_create_project(self):
        project = Project.objects.create(name='Proj1', owner=self.user)
        self.assertEqual(project.owner, self.user)

    def test_create_task(self):
        project = Project.objects.create(name='Proj1',owner=self.user)
        task = Task.objects.create(project, title='Task1', due_date="01-09-2025",)
        self.assertEqual(task.project, project)

    def test_only_owner_can_delete_project(self):
        project = Project.objects.create(name='Proj1', owner=self.user)
        response = self.client.post(f"/projects/{project.pk}/delete/")
        self.assertEqual(response.status_code,302)
