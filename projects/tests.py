from django.contrib.auth import get_user_model
from unittest.mock import patch
from rest_framework.test import APITestCase
from rest_framework import status

from .models import Project, Task
from erp_foundation.services import create_workspace
from erp_foundation.testing import add_member

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
        self.tenant = create_workspace(self.owner, 'Team')
        add_member(self.tenant, self.admin, admin=True)
        add_member(self.tenant, self.manager, manager=True)
        add_member(self.tenant, self.member)
        add_member(self.tenant, self.outsider)
        self.project = Project.objects.create(name='Proj1', owner=self.owner, tenant=self.tenant)
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


class TaskBoundaryTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(email='owner@example.com', password='pass123')
        self.outsider = User.objects.create_user(email='outside@example.com', password='pass123')
        self.tenant = create_workspace(self.owner, 'Team')
        other_tenant = create_workspace(self.outsider, 'Private')
        self.project = Project.objects.create(name='Team', owner=self.owner, tenant=self.tenant)
        self.other_project = Project.objects.create(name='Private', owner=self.outsider, tenant=other_tenant)
        self.task = Task.objects.create(project=self.project, title='Original')
        self.client.force_authenticate(self.owner)

    def update_task(self, data):
        return self.client.patch(f'/api/tasks/{self.task.pk}/', data, format='json')

    def test_cannot_move_task_into_another_project(self):
        response = self.update_task({'project': self.other_project.pk})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.task.refresh_from_db()
        self.assertEqual(self.task.project_id, self.project.pk)

    def test_cannot_assign_outsider_on_create_or_update(self):
        response = self.client.post('/api/tasks/', {
            'project': self.project.pk, 'title': 'Leak', 'assigned_to': self.outsider.pk,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Task.objects.filter(title='Leak').exists())
        self.assertEqual(self.update_task({'assigned_to': self.outsider.pk}).status_code, 400)
        self.task.refresh_from_db()
        self.assertIsNone(self.task.assigned_to_id)

    def test_cannot_assign_inactive_member(self):
        self.project.members.add(self.outsider)
        self.outsider.is_active = False
        self.outsider.save()
        self.assertEqual(self.update_task({'assigned_to': self.outsider.pk}).status_code, 400)

    @patch('projects.api_views.send_async')
    @patch('projects.api_views.TaskViewSet._notify_task_update')
    def test_can_assign_member_and_clear_assignment(self, notify, email):
        add_member(self.tenant, self.outsider)
        self.project.members.add(self.outsider)
        self.assertEqual(self.update_task({'assigned_to': self.outsider.pk}).status_code, 200)
        self.task.refresh_from_db()
        self.assertEqual(self.task.assigned_to_id, self.outsider.pk)
        self.assertEqual(self.update_task({'assigned_to': None}).status_code, 200)
        self.task.refresh_from_db()
        self.assertIsNone(self.task.assigned_to_id)

    def test_rejects_self_parent_and_descendant_parent(self):
        child = Task.objects.create(project=self.project, title='Child', parent=self.task)
        for parent in (self.task, child):
            with self.subTest(parent=parent.pk):
                self.assertEqual(self.update_task({'parent': parent.pk}).status_code, 400)

    def test_rejects_cross_project_relationships_and_self_link(self):
        private = Task.objects.create(project=self.other_project, title='Private')
        for data in ({'parent': private.pk}, {'linked_tasks': [private.pk]}, {'linked_tasks': [self.task.pk]}):
            with self.subTest(data=data):
                self.assertEqual(self.update_task(data).status_code, 400)

    @patch('projects.api_views.TaskViewSet._notify_task_update')
    def test_allows_same_project_relationships(self, notify):
        sibling = Task.objects.create(project=self.project, title='Sibling')
        response = self.update_task({'project': self.project.pk, 'parent': sibling.pk, 'linked_tasks': [sibling.pk]})
        self.assertEqual(response.status_code, 200)
        self.task.refresh_from_db()
        self.assertEqual(self.task.parent_id, sibling.pk)
        self.assertEqual(list(self.task.linked_tasks.all()), [sibling])
