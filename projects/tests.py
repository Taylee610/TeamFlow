from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status

from .models import Project, Task

User = get_user_model()


class ProjectTaskModelTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='test@example.com', password='pass123')

    def test_create_project(self):
        project = Project.objects.create(name='Proj1', owner=self.user)
        self.assertEqual(project.owner, self.user)

    def test_create_task(self):
        project = Project.objects.create(name='Proj1', owner=self.user)
        task = Task.objects.create(project=project, title='Task1', due_date='2025-09-01T00:00:00Z')
        self.assertEqual(task.project, project)


class ProjectPermissionTests(APITestCase):
    """RBAC: owner/Admin/Manager/Member behavior for project & task management."""

    def setUp(self):
        self.owner = User.objects.create_user(email='owner@example.com', password='pass123')
        self.admin = User.objects.create_user(email='admin@example.com', password='pass123', role=User.Role.ADMIN)
        self.manager = User.objects.create_user(email='manager@example.com', password='pass123', role=User.Role.MANAGER)
        self.member = User.objects.create_user(email='member@example.com', password='pass123')
        self.outsider = User.objects.create_user(email='outsider@example.com', password='pass123')

        self.project = Project.objects.create(name='Proj1', owner=self.owner)
        self.project.members.add(self.manager, self.member)

        self.task = Task.objects.create(project=self.project, title='Task1')

    def test_owner_can_delete_project(self):
        self.client.force_authenticate(self.owner)
        response = self.client.delete(f'/api/projects/{self.project.pk}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_admin_can_delete_any_project(self):
        self.client.force_authenticate(self.admin)
        response = self.client.delete(f'/api/projects/{self.project.pk}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_manager_member_can_delete_project(self):
        self.client.force_authenticate(self.manager)
        response = self.client.delete(f'/api/projects/{self.project.pk}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_plain_member_cannot_delete_project(self):
        self.client.force_authenticate(self.member)
        response = self.client.delete(f'/api/projects/{self.project.pk}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Project.objects.filter(pk=self.project.pk).exists())

    def test_outsider_cannot_see_project(self):
        self.client.force_authenticate(self.outsider)
        response = self.client.get(f'/api/projects/{self.project.pk}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_manager_member_can_add_and_remove_members(self):
        self.client.force_authenticate(self.manager)
        add_response = self.client.post(
            f'/api/projects/{self.project.pk}/members/', {'email': self.outsider.email}
        )
        self.assertEqual(add_response.status_code, status.HTTP_201_CREATED)

        remove_response = self.client.delete(f'/api/projects/{self.project.pk}/members/{self.outsider.pk}/')
        self.assertEqual(remove_response.status_code, status.HTTP_200_OK)

    def test_plain_member_cannot_add_members(self):
        self.client.force_authenticate(self.member)
        response = self.client.post(
            f'/api/projects/{self.project.pk}/members/', {'email': self.outsider.email}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_manager_member_can_delete_task(self):
        self.client.force_authenticate(self.manager)
        response = self.client.delete(f'/api/tasks/{self.task.pk}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_plain_member_cannot_delete_task(self):
        self.client.force_authenticate(self.member)
        response = self.client.delete(f'/api/tasks/{self.task.pk}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Task.objects.filter(pk=self.task.pk).exists())

    def test_admin_can_delete_any_task(self):
        self.client.force_authenticate(self.admin)
        response = self.client.delete(f'/api/tasks/{self.task.pk}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
