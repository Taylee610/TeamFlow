from datetime import timedelta
from io import StringIO
from django.test import override_settings
from django.utils import timezone
from django.core.management import call_command
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from erp_foundation.services import create_workspace
from projects.models import Project, Task
from .ml import plan, project_insights


@override_settings(TAYLEE_ENGINE='local_ml')
class LocalMLTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(email='ml@example.test', password='Test-pass-934!')
        self.tenant = create_workspace(self.user, 'ML workspace')
        self.project = Project.objects.create(tenant=self.tenant, owner=self.user, name='ML project')
        self.client.force_authenticate(self.user)

    def test_offline_plan_and_unknown_intent(self):
        response = self.client.post('/api/ai/task-assist/', {'prompt': 'Review overdue customer invoices'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['engine'], 'local_ml')
        self.assertEqual(response.data['intent'], 'finance')
        self.assertEqual(plan('xyzzy quux')['intent'], 'general')

    def test_foreign_workspace_denied(self):
        other = create_workspace(self.user, 'Other')
        project = Project.objects.create(tenant=other, owner=self.user, name='Other')
        response = self.client.get(f'/api/ai/projects/{project.pk}/summary/', HTTP_X_WORKSPACE_ID=str(self.tenant.pk))
        self.assertEqual(response.status_code, 403)

    def test_no_prediction_without_history(self):
        Task.objects.create(project=self.project, title='Late', due_date=timezone.now()-timedelta(days=1))
        data = project_insights(self.project, Project.objects.filter(tenant=self.tenant))
        self.assertFalse(data['model']['available'])
        self.assertTrue(data['risks'][0]['already_overdue'])
        self.assertIsNone(data['risks'][0]['late_probability'])

    def test_save_plan_is_atomic_and_retry_safe(self):
        import uuid
        payload = {'project': self.project.pk, 'title': 'Review invoices', 'request_key': str(uuid.uuid4()), 'plan': plan('Review overdue customer invoices')}
        response = self.client.post('/api/ai/save-plan/', payload, format='json')
        self.assertEqual(response.status_code, 201)
        count = Task.objects.count()
        self.assertEqual(self.client.post('/api/ai/save-plan/', payload, format='json').status_code, 200)
        self.assertEqual(Task.objects.count(), count)
        payload['title'] = 'Different plan'
        self.assertEqual(self.client.post('/api/ai/save-plan/', payload, format='json').status_code, 409)
        payload['request_key'] = str(uuid.uuid4())
        payload['plan']['due_date'] = 'invalid-date'
        self.assertEqual(self.client.post('/api/ai/save-plan/', payload, format='json').status_code, 400)
        self.assertEqual(Task.objects.count(), count)

    def test_learned_model_and_temporal_validation(self):
        now = timezone.now()
        for i in range(40):
            late = i % 2 == 0
            task = Task.objects.create(project=self.project, title=str(i), status='done', due_date=now-timedelta(days=50-i), priority='high' if late else 'low', story_points=8 if late else 2)
            Task.objects.filter(pk=task.pk).update(created_at=task.due_date-timedelta(days=2 if late else 12), completed_at=task.due_date+timedelta(days=1 if late else -1))
        Task.objects.create(project=self.project, title='Future', due_date=now+timedelta(days=2), priority='high', story_points=8)
        data = project_insights(self.project, Project.objects.filter(tenant=self.tenant))
        self.assertTrue(data['model']['available'])
        self.assertEqual(data['model']['validation']['samples'], 8)
        self.assertGreater(data['risks'][0]['late_probability'], .5)

    def test_demo_history_does_not_train_real_project(self):
        demo = Project.objects.create(tenant=self.tenant, owner=self.user, name='Demo · Training')
        now = timezone.now()
        for i in range(40):
            due = now-timedelta(days=40-i)
            task = Task.objects.create(project=demo, title=str(i), status='done', due_date=due, labels=['demo'])
            Task.objects.filter(pk=task.pk).update(created_at=due-timedelta(days=5), completed_at=due+timedelta(days=1 if i%2 else -1))
        data = project_insights(self.project, Project.objects.filter(tenant=self.tenant))
        self.assertEqual(data['model']['training_samples'], 0)
        self.assertFalse(data['model']['available'])
