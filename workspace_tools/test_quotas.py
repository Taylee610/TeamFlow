from datetime import timedelta
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APITestCase
from erp_foundation.services import create_workspace
from erp_foundation.testing import add_member
from erp_operations.models import SaaSPlan, TenantSubscription
from projects.models import Project
from .models import UsageCounter, BillingPayment
from .billing import subscription_for, active_subscription
from .quotas import reserve_ai_request


class QuotaTests(APITestCase):
    def setUp(self):
        self.user=get_user_model().objects.create_user(email='quota@example.com',password='pass')
        self.tenant=create_workspace(self.user,'Quota')
        self.client.force_authenticate(self.user)
        self.subscription=subscription_for(self.tenant)

    def set_limit(self,key,value):
        plan=self.subscription.plan
        plan.limits={**plan.limits,key:value};plan.save()

    def test_ai_meter_denies_before_provider_call(self):
        self.set_limit('ai',1)
        reserve_ai_request(self.tenant)
        from rest_framework.exceptions import ValidationError
        with self.assertRaises(ValidationError):reserve_ai_request(self.tenant)
        self.assertEqual(UsageCounter.objects.get().count,1)

    def test_task_upload_denied_when_storage_quota_full(self):
        self.set_limit('storage_mb',0)
        project=Project.objects.create(tenant=self.tenant,owner=self.user,name='Files')
        response=self.client.post('/api/tasks/',{'project':project.pk,'title':'File','attachment':SimpleUploadedFile('note.txt',b'example')},format='multipart')
        self.assertEqual(response.status_code,400,response.data)

    def test_invitation_seat_limit_checked_at_acceptance(self):
        self.set_limit('seats',1)
        guest=get_user_model().objects.create_user(email='guest@example.com',password='pass')
        result=self.client.post('/api/workspaces/invitations/',{'email':guest.email})
        from urllib.parse import parse_qs,urlparse
        token=parse_qs(urlparse(result.data['invite_url']).query)['invite'][0]
        self.client.force_authenticate(guest)
        response=self.client.post('/api/workspaces/invitations/accept/',{'token':token})
        self.assertEqual(response.status_code,400,response.data)

    def test_trial_once_and_expiry(self):
        plan=SaaSPlan.objects.create(name='Pro',monthly_price=10,is_public=True,limits={})
        response=self.client.post('/api/tools/billing/trial/',{'plan':plan.pk})
        self.assertEqual(response.status_code,200,response.data)
        self.assertEqual(active_subscription(self.tenant).status,'trial')
        self.assertEqual(self.client.post('/api/tools/billing/trial/',{'plan':plan.pk}).status_code,400)
        subscription=TenantSubscription.objects.get(tenant=self.tenant)
        subscription.trial_ends_at=timezone.now()-timedelta(seconds=1);subscription.save()
        self.assertEqual(self.client.post('/api/tools/habits/',{'name':'Routine'}).status_code,403)
        self.assertEqual(self.client.patch('/api/tools/billing/',{'action':'free'}).status_code,200)
        self.assertEqual(self.client.post('/api/tools/billing/trial/',{'plan':plan.pk}).status_code,400)

    def test_trial_can_return_to_free_without_resetting_eligibility(self):
        plan=SaaSPlan.objects.create(name='Trial',monthly_price=10,is_public=True)
        self.client.post('/api/tools/billing/trial/',{'plan':plan.pk})
        self.assertEqual(self.client.patch('/api/tools/billing/',{'action':'free'}).status_code,200)
        subscription=TenantSubscription.objects.get(tenant=self.tenant)
        self.assertEqual(subscription.plan.name,'Free')
        self.assertTrue(subscription.trial_used)
