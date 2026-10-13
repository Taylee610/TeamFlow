from datetime import timedelta
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APITestCase
from erp_foundation.services import create_workspace
from erp_foundation.testing import add_member
from erp_foundation.models import AuditLog
from .models import Job, Monitor, MonitorCheck, Habit, HabitLog, Form, FormResponse, Deck, Flashcard, CardProgress, FeedbackWidget, Feedback, Client
from .services import check_monitor, probe, run_one

User = get_user_model()


class ToolTests(APITestCase):
    def setUp(self):
        self.user=User.objects.create_user(email='owner@example.com', password='pass')
        self.other=User.objects.create_user(email='other@example.com', password='pass')
        self.tenant=create_workspace(self.user,'One')
        self.other_tenant=create_workspace(self.other,'Two')
        self.client.force_authenticate(self.user)

    def test_all_tools_reject_cross_workspace_reads_and_updates(self):
        records=[('monitors', Monitor.objects.create(tenant=self.other_tenant,created_by=self.other,name='Private',url='https://example.com')),
                 ('clients',Client.objects.create(tenant=self.other_tenant,created_by=self.other,name='Private')),
                 ('habits',Habit.objects.create(tenant=self.other_tenant,created_by=self.other,name='Private')),
                 ('forms',Form.objects.create(tenant=self.other_tenant,created_by=self.other,title='Private')),
                 ('decks',Deck.objects.create(tenant=self.other_tenant,created_by=self.other,name='Private',shared=True))]
        for path,record in records:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(f'/api/tools/{path}/{record.pk}/').status_code,404)
                self.assertEqual(self.client.patch(f'/api/tools/{path}/{record.pk}/',{'name':'Stolen'}).status_code,404)

    def test_habits_private_to_owner_and_logs_idempotent(self):
        add_member(self.tenant,self.other,admin=True)
        habit=Habit.objects.create(tenant=self.tenant,created_by=self.user,name='Daily')
        for _ in range(2):
            self.assertEqual(self.client.post(f'/api/tools/habits/{habit.pk}/logs/',{'completed':True}).status_code,200)
        self.assertEqual(HabitLog.objects.filter(habit=habit).count(),1)
        self.assertEqual(self.client.get(f'/api/tools/habits/{habit.pk}/logs/').data['streak'],1)
        self.client.force_authenticate(self.other)
        self.client.credentials(HTTP_X_WORKSPACE_ID=str(self.tenant.pk))
        self.assertEqual(self.client.get(f'/api/tools/habits/{habit.pk}/').status_code,404)

    def test_public_form_validation_and_schema_history(self):
        fields=[{'key':'name','type':'text','label':'Name','required':True}]
        response=self.client.post('/api/tools/forms/',{'title':'Intake','published':True,'fields':fields},format='json')
        self.assertEqual(response.status_code,201,response.data)
        form=Form.objects.get(pk=response.data['id'])
        self.client.force_authenticate(None)
        url=f'/api/tools/public/forms/{form.public_id}/'
        self.assertEqual(self.client.post(url,{'version':1,'answers':{}},format='json').status_code,400)
        self.assertEqual(self.client.post(url,{'version':1,'answers':{'name':'Alice'}},format='json').status_code,201)
        self.client.force_authenticate(self.user)
        self.client.patch(f'/api/tools/forms/{form.pk}/',{'fields':[{'key':'email','type':'email','label':'Email','required':True}]},format='json')
        form.refresh_from_db()
        self.assertEqual(form.version,2)
        self.assertEqual(FormResponse.objects.get().schema[0]['key'],'name')
        self.client.force_authenticate(None)
        self.assertEqual(self.client.post(url,{'version':1,'answers':{'name':'Alice'}},format='json').status_code,400)

    def test_private_profiles_and_unsafe_links(self):
        response=self.client.post('/api/tools/profiles/',{'slug':'company','title':'Company','links':[{'label':'Bad','url':'javascript:alert(1)'}]},format='json')
        self.assertEqual(response.status_code,400)
        response=self.client.post('/api/tools/profiles/',{'slug':'company','title':'Company','links':[{'label':'Home','url':'https://example.com'}]},format='json')
        self.assertEqual(response.status_code,201)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get('/api/tools/public/profiles/company/').status_code,404)

    def test_card_progress_per_user_and_retry_safe(self):
        add_member(self.tenant,self.other)
        deck=Deck.objects.create(tenant=self.tenant,created_by=self.user,name='Team',shared=True)
        card=Flashcard.objects.create(tenant=self.tenant,created_by=self.user,deck=deck,question='Q',answer='A')
        payload={'rating':'easy','request_key':'a65a7b20-044e-4ee5-9a7f-b4414d89a23e'}
        for _ in range(2):
            self.assertEqual(self.client.post(f'/api/tools/cards/{card.pk}/review/',payload).status_code,200)
        self.assertEqual(CardProgress.objects.get().reviews,1)
        self.assertEqual(self.client.get(f'/api/tools/decks/{deck.pk}/study/').data,[])
        self.client.force_authenticate(self.other);self.client.credentials(HTTP_X_WORKSPACE_ID=str(self.tenant.pk))
        self.assertEqual(len(self.client.get(f'/api/tools/decks/{deck.pk}/study/').data),1)
        self.assertEqual(self.client.patch(f'/api/tools/cards/{card.pk}/',{'answer':'Changed'}).status_code,403)

    def test_widget_registered_origin_and_conversion(self):
        widget=FeedbackWidget.objects.create(tenant=self.tenant,created_by=self.user,name='Site',allowed_origins=['https://example.com'])
        url=f'/api/tools/public/widgets/{widget.public_id}/'
        self.client.force_authenticate(None)
        self.assertEqual(self.client.post(url,{'message':'Hi'},HTTP_ORIGIN='https://evil.com').status_code,403)
        response=self.client.post(url,{'message':'Please add search'},HTTP_ORIGIN='https://example.com')
        self.assertEqual(response.status_code,201)
        self.assertEqual(response['Access-Control-Allow-Origin'],'https://example.com')
        self.client.force_authenticate(self.user)
        project=self.client.post('/api/projects/',{'name':'Website'}).data['id']
        feedback=Feedback.objects.get()
        path=f'/api/tools/feedback/{feedback.pk}/create-task/'
        first=self.client.post(path,{'project':project}).data
        self.assertEqual(self.client.post(path,{'project':project}).data['task'],first['task'])

    @patch('workspace_tools.services.probe')
    def test_monitor_transition_alerts_are_deduplicated(self, mocked):
        monitor=Monitor.objects.create(tenant=self.tenant,created_by=self.user,name='Site',url='https://example.com')
        mocked.return_value=(False,500,12,'')
        check_monitor(monitor.pk);check_monitor(monitor.pk)
        self.assertEqual(Job.objects.filter(kind='email').count(),1)
        mocked.return_value=(True,200,10,'')
        check_monitor(monitor.pk)
        self.assertEqual(Job.objects.filter(kind='email').count(),2)
        monitor.refresh_from_db();self.assertIsNone(monitor.incident_started_at)

    @patch('workspace_tools.services.socket.getaddrinfo')
    def test_monitor_blocks_internal_addresses(self, mocked):
        mocked.return_value=[(2,1,6,'',('127.0.0.1',443))]
        with self.assertRaises(ValueError):probe('https://example.com')
        mocked.return_value=[(2,1,6,'',('169.254.169.254',80))]
        with self.assertRaises(ValueError):probe('http://example.com')

    @patch('workspace_tools.services.execute_job',side_effect=RuntimeError('Temporary failure'))
    def test_worker_persists_retry_and_recovers_expired_lease(self, mocked):
        job=Job.objects.create(kind='email',dedup_key='one',payload={})
        self.assertTrue(run_one());job.refresh_from_db()
        self.assertEqual(job.status,'pending');self.assertEqual(job.attempts,1)
        job.status='running';job.locked_until=timezone.now()-timedelta(seconds=1);job.save()
        self.assertTrue(run_one());job.refresh_from_db();self.assertEqual(job.attempts,2)

    def test_mutations_create_audit_events(self):
        response=self.client.post('/api/tools/clients/',{'name':'Client'})
        self.assertEqual(response.status_code,201)
        self.assertTrue(AuditLog.objects.filter(tenant=self.tenant,action='create',object_type='workspace_tools.Client').exists())

    def test_crm_rejects_linking_other_workspace_project(self):
        from projects.models import Project
        project=Project.objects.create(tenant=self.other_tenant,owner=self.other,name='Private')
        self.assertEqual(self.client.post('/api/tools/clients/',{'name':'Client','projects':[project.pk]},format='json').status_code,400)

    def test_preferences_are_account_scoped(self):
        self.client.patch('/api/tools/preferences/',{'email_notifications':False},format='json')
        self.assertFalse(self.client.get('/api/tools/preferences/').data['email_notifications'])
        self.client.force_authenticate(self.other)
        self.assertTrue(self.client.get('/api/tools/preferences/').data['email_notifications'])

    def test_role_management_and_last_admin_protection(self):
        membership=add_member(self.tenant,self.other)
        response=self.client.post('/api/workspaces/roles/',{'name':'Finance','permissions':['finance.view']},format='json')
        self.assertEqual(response.status_code,201,response.data)
        path=f'/api/workspaces/members/{membership.pk}/'
        self.assertEqual(self.client.patch(path,{'role_id':response.data['id']}).status_code,200)
        from erp_foundation.models import Membership
        owner=Membership.objects.get(tenant=self.tenant,user=self.user)
        self.assertEqual(self.client.patch(f'/api/workspaces/members/{owner.pk}/',{'is_active':False},format='json').status_code,400)
        self.assertEqual(self.client.patch(path,{'is_active':False},format='json').status_code,200)

    def test_audit_queryset_cannot_change_or_delete_events(self):
        from django.core.exceptions import ValidationError
        self.client.post('/api/tools/clients/',{'name':'Client'})
        with self.assertRaises(ValidationError):AuditLog.objects.all().update(action='hidden')
        with self.assertRaises(ValidationError):AuditLog.objects.all().delete()
