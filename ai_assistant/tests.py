import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status

from projects.models import Project, Task

User = get_user_model()


def _fake_message(text):
    return SimpleNamespace(content=[SimpleNamespace(type='text', text=text)])


class TaskAssistViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='user@example.com', password='pass123')
        self.client.force_authenticate(self.user)

    @patch('ai_assistant.views.get_client', return_value=None)
    def test_returns_503_when_key_missing(self, mock_get_client):
        response = self.client.post('/api/ai/task-assist/', {'prompt': 'Set up CI'})
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    @patch('ai_assistant.views.get_client')
    def test_returns_structured_fields(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _fake_message(json.dumps({
            'description': 'Set up a CI pipeline for the backend.',
            'subtasks': ['Add GitHub Actions workflow', 'Run tests on push'],
            'priority': 'high',
            'due_date': None,
        }))
        mock_get_client.return_value = mock_client

        response = self.client.post('/api/ai/task-assist/', {'prompt': 'Set up CI for backend'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['priority'], 'high')
        self.assertEqual(len(response.data['subtasks']), 2)

    def test_requires_authentication(self):
        self.client.force_authenticate(None)
        response = self.client.post('/api/ai/task-assist/', {'prompt': 'Set up CI'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ProjectSummaryViewTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(email='owner@example.com', password='pass123')
        self.outsider = User.objects.create_user(email='outsider@example.com', password='pass123')
        self.project = Project.objects.create(name='Proj1', owner=self.owner)
        Task.objects.create(project=self.project, title='Task1')

    @patch('ai_assistant.views.get_client', return_value=None)
    def test_returns_503_when_key_missing(self, mock_get_client):
        self.client.force_authenticate(self.owner)
        response = self.client.get(f'/api/ai/projects/{self.project.id}/summary/')
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    @patch('ai_assistant.views.get_client')
    def test_returns_summary_for_owner(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _fake_message('Everything is on track.')
        mock_get_client.return_value = mock_client

        self.client.force_authenticate(self.owner)
        response = self.client.get(f'/api/ai/projects/{self.project.id}/summary/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['summary'], 'Everything is on track.')

    @patch('ai_assistant.views.get_client')
    def test_non_member_forbidden(self, mock_get_client):
        mock_get_client.return_value = MagicMock()
        self.client.force_authenticate(self.outsider)
        response = self.client.get(f'/api/ai/projects/{self.project.id}/summary/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
