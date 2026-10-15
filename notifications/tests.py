from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.management import call_command
from django.test import TestCase
from django.db import connection
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APITestCase
from rest_framework import status

from projects.models import Project, Task
from .emails import send_task_assigned_email, send_due_date_reminder_email
from erp_foundation.services import create_workspace
from erp_foundation.testing import add_member

User = get_user_model()


class EmailContentTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(email='owner@example.com', password='pass123')
        self.assignee = User.objects.create_user(email='assignee@example.com', password='pass123', first_name='Sam')
        self.project = Project.objects.create(name='Proj1', owner=self.owner)
        self.task = Task.objects.create(project=self.project, title='Write docs', assigned_to=self.assignee)

    def test_send_task_assigned_email(self):
        send_task_assigned_email(self.task, assigned_by=self.owner)
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, ['assignee@example.com'])
        self.assertIn('Write docs', email.subject)

    def test_send_task_assigned_email_no_assignee_is_noop(self):
        self.task.assigned_to = None
        self.task.save()
        send_task_assigned_email(self.task, assigned_by=self.owner)
        self.assertEqual(len(mail.outbox), 0)

    def test_send_due_date_reminder_email(self):
        send_due_date_reminder_email(self.task)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Write docs', mail.outbox[0].subject)


class SendDueRemindersCommandTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(email='owner@example.com', password='pass123')
        self.assignee = User.objects.create_user(email='assignee@example.com', password='pass123')
        tenant = create_workspace(self.owner, 'Reminder team')
        add_member(tenant, self.assignee)
        self.project = Project.objects.create(name='Proj1', owner=self.owner, tenant=tenant)
        self.project.members.add(self.assignee)
        self.task = Task.objects.create(
            project=self.project,
            title='Due soon task',
            assigned_to=self.assignee,
            due_date=timezone.now() + timedelta(hours=6),
        )

    def test_sends_reminder_and_marks_sent(self):
        call_command('send_due_reminders')
        self.assertEqual(len(mail.outbox), 0)
        call_command('run_worker', once=True)
        self.assertEqual(len(mail.outbox), 1)
        self.task.refresh_from_db()
        self.assertIsNotNone(self.task.reminder_sent_at)

    def test_does_not_resend(self):
        call_command('send_due_reminders')
        call_command('send_due_reminders')
        call_command('run_worker', once=True)
        self.assertEqual(len(mail.outbox), 1)

    def test_worker_preserves_callers_transaction(self):
        call_command('send_due_reminders')
        # SQLite ignores close() for its in-memory test database; detect the
        # attempted close as well as checking actual job delivery and DB reuse.
        with patch.object(connection, 'close') as close:
            call_command('run_worker', once=True)
            close.assert_not_called()
        self.task.refresh_from_db()
        self.assertIsNotNone(self.task.reminder_sent_at)
        self.assertEqual(len(mail.outbox), 1)

    def test_ignores_tasks_outside_window(self):
        self.task.due_date = timezone.now() + timedelta(days=5)
        self.task.save()
        call_command('send_due_reminders')
        self.assertEqual(len(mail.outbox), 0)


class TaskAssignmentTriggersEmailTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(email='owner@example.com', password='pass123')
        self.assignee = User.objects.create_user(email='assignee@example.com', password='pass123')
        self.tenant = create_workspace(self.owner, 'Team')
        add_member(self.tenant, self.assignee)
        self.project = Project.objects.create(name='Proj1', owner=self.owner, tenant=self.tenant)
        self.project.members.add(self.assignee)
        self.client.force_authenticate(self.owner)

    @patch('projects.api_views.send_async')
    def test_creating_assigned_task_sends_email(self, mock_send_async):
        response = self.client.post('/api/tasks/', {
            'project': self.project.id,
            'title': 'New task',
            'assigned_to': self.assignee.id,
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        mock_send_async.assert_called_once()

    @patch('projects.api_views.send_async')
    def test_unrelated_update_does_not_resend(self, mock_send_async):
        task = Task.objects.create(project=self.project, title='Task1', assigned_to=self.assignee)
        response = self.client.patch(f'/api/tasks/{task.id}/', {'status': 'in_progress'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_send_async.assert_not_called()

    @patch('projects.api_views.send_async')
    def test_reassignment_sends_email(self, mock_send_async):
        other = User.objects.create_user(email='other@example.com', password='pass123')
        add_member(self.tenant, other)
        self.project.members.add(other)
        task = Task.objects.create(project=self.project, title='Task1', assigned_to=self.assignee)
        response = self.client.patch(f'/api/tasks/{task.id}/', {'assigned_to': other.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_send_async.assert_called_once()
