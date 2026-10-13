from datetime import timedelta
from decimal import Decimal
from urllib.parse import urlencode
from unittest.mock import patch
from django.test import override_settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase
from erp_foundation.services import create_workspace
from erp_operations.models import SaaSPlan, TenantSubscription
from .models import BillingPayment, BillingEvent, Job
from .billing import sign_fields, verified_fields, verify_payment, provider_url, subscription_for, active_subscription


@override_settings(PAYNOW_INTEGRATION_ID='123', PAYNOW_INTEGRATION_KEY='test-merchant-secret', PAYNOW_RESULT_URL='https://api.example.com/api/tools/billing/paynow/result/')
class BillingTests(APITestCase):
    def setUp(self):
        self.user=get_user_model().objects.create_user(email='billing@example.com',password='pass')
        self.tenant=create_workspace(self.user,'Billing')
        self.plan=SaaSPlan.objects.create(name='Business',monthly_price=Decimal('10'),currency='USD',is_public=True,limits={'monitors':50})
        self.client.force_authenticate(self.user)

    def payment(self):
        return BillingPayment.objects.create(tenant=self.tenant,created_by=self.user,plan=self.plan,amount=10,request_key='a3c143a2-5874-4fd2-860e-29562dc976ed',poll_url='https://www.paynow.co.zw/interface/checkpayment/?guid=known',status='pending')

    def status(self,payment,status='Paid',amount='10.00'):
        return {'reference':payment.reference.hex,'amount':amount,'paynowreference':'1234','pollurl':payment.poll_url,'status':status}

    def test_checkout_is_queued_once_and_uses_server_price(self):
        payload={'plan':self.plan.pk,'method':'paynow','amount':'0.01','request_key':'a3c143a2-5874-4fd2-860e-29562dc976ed'}
        for _ in range(2):
            self.assertEqual(self.client.post('/api/tools/billing/checkout/',payload).status_code,202)
        self.assertEqual(BillingPayment.objects.get().amount,Decimal('10'))
        self.assertEqual(Job.objects.filter(kind='billing_start').count(),1)

    def test_webhook_signature_amount_and_duplicate_protection(self):
        payment=self.payment();values=list(self.status(payment).items());values += [('hash',sign_fields(values))]
        raw=urlencode(values)
        self.client.force_authenticate(None)
        path='/api/tools/billing/paynow/result/'
        self.assertEqual(self.client.post(path,raw,content_type='application/x-www-form-urlencoded').status_code,200)
        self.assertEqual(self.client.post(path,raw,content_type='application/x-www-form-urlencoded').status_code,200)
        self.assertEqual(BillingEvent.objects.count(),1)
        self.assertEqual(Job.objects.filter(kind='billing_verify').count(),1)
        self.assertEqual(self.client.post(path,raw.replace('10.00','99.00'),content_type='application/x-www-form-urlencoded').status_code,400)
        self.assertIsNone(BillingPayment.objects.get().granted_at)

    @patch('workspace_tools.billing.exchange')
    def test_paid_status_grants_once_and_refund_suspends(self,mocked):
        payment=self.payment();mocked.return_value=self.status(payment)
        verify_payment(payment.pk)
        subscription=TenantSubscription.objects.get(tenant=self.tenant);until=subscription.paid_until
        verify_payment(payment.pk);subscription.refresh_from_db();self.assertEqual(subscription.paid_until,until)
        mocked.return_value=self.status(payment,'Refunded');verify_payment(payment.pk)
        subscription.refresh_from_db();self.assertEqual(subscription.status,'suspended')

    @patch('workspace_tools.billing.exchange')
    def test_all_successful_provider_states_are_recognized(self,mocked):
        payment=self.payment()
        for status in ('Awaiting Delivery','Delivered','Paid'):
            mocked.return_value=self.status(payment,status);verify_payment(payment.pk)
        payment.refresh_from_db();self.assertEqual(payment.status,'paid')
        self.assertEqual(TenantSubscription.objects.get(tenant=self.tenant).plan_id,self.plan.pk)

    @patch('workspace_tools.billing.exchange')
    def test_poll_amount_mismatch_never_grants_access(self,mocked):
        payment=self.payment();mocked.return_value=self.status(payment,amount='1.00')
        with self.assertRaises(ValueError):verify_payment(payment.pk)
        payment.refresh_from_db();self.assertIsNone(payment.granted_at)

    def test_provider_url_and_duplicate_fields_rejected(self):
        for url in ('http://www.paynow.co.zw/x','https://paynow.co.zw.evil.com/x','https://127.0.0.1/x'):
            with self.assertRaises(ValueError):provider_url(url)
        values=[('status','Paid'),('amount','10.00')];values+=[('hash',sign_fields(values))]
        self.assertEqual(verified_fields(urlencode(values))['status'],'Paid')
        with self.assertRaises(ValueError):verified_fields(urlencode(values)+'&status=Cancelled')

    def test_expired_subscription_denies_writes_but_preserves_reads(self):
        subscription=subscription_for(self.tenant);subscription.plan=self.plan;subscription.paid_until=timezone.now()-timedelta(days=1);subscription.save()
        self.assertEqual(self.client.post('/api/tools/monitors/',{'name':'Site','url':'https://example.com'}).status_code,403)
        self.assertEqual(self.client.get('/api/tools/monitors/').status_code,200)
        subscription.cancel_at_period_end=True;subscription.save()
        self.assertEqual(active_subscription(self.tenant).plan.name,'Free')

    def test_plan_limits_enforced_on_server(self):
        free=subscription_for(self.tenant).plan;free.limits={'monitors':0};free.save()
        self.assertEqual(self.client.post('/api/tools/monitors/',{'name':'Site','url':'https://example.com'}).status_code,400)
