import hashlib
import hmac
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from urllib.parse import parse_qsl, urlsplit
import httpx
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers, permissions
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from erp_foundation.access import workspace_membership, can_admin_workspace
from erp_operations.models import SaaSPlan, TenantSubscription
from .models import BillingPayment, BillingEvent, Job
from .services import enqueue, audit

DEFAULT_LIMITS = {'monitors': 30, 'clients': 500, 'profiles': 10, 'habits': 100, 'decks': 100, 'cards': 10000, 'forms': 100, 'widgets': 30, 'wiki': 500, 'approvals': 500, 'time': 10000, 'seats': 20, 'ai': 20, 'storage_mb': 100}


def subscription_for(tenant):
    existing = TenantSubscription.objects.filter(tenant=tenant).select_related('plan').first()
    if existing:
        return existing
    plan = SaaSPlan.objects.filter(name='Free', monthly_price=0).first()
    if not plan:
        plan = SaaSPlan.objects.create(name='Free', monthly_price=0, limits=DEFAULT_LIMITS, is_public=True)
    return TenantSubscription.objects.get_or_create(tenant=tenant, defaults={'plan': plan, 'starts_on': timezone.now().date(), 'status': 'active'})[0]


def active_subscription(tenant):
    subscription = subscription_for(tenant)
    if subscription.cancel_at_period_end and subscription.paid_until and subscription.paid_until <= timezone.now():
        with transaction.atomic():
            subscription = TenantSubscription.objects.select_for_update().get(pk=subscription.pk)
            if subscription.cancel_at_period_end and subscription.paid_until <= timezone.now():
                free = SaaSPlan.objects.filter(name='Free', monthly_price=0).first()
                if not free:
                    free = SaaSPlan.objects.create(name='Free', monthly_price=0, limits=DEFAULT_LIMITS, is_public=True)
                subscription.plan, subscription.status, subscription.paid_until, subscription.cancel_at_period_end = free, 'active', None, False
                subscription.save()
    if subscription.status == 'trial' and subscription.trial_ends_at and subscription.trial_ends_at > timezone.now():
        return subscription
    if subscription.status != 'active' or (subscription.plan.monthly_price > 0 and (not subscription.paid_until or subscription.paid_until <= timezone.now())):
        raise PermissionDenied('This workspace subscription is inactive or expired. Its administrator can renew or select the free plan.')
    return subscription


def limit_for(tenant, module, fallback):
    subscription = active_subscription(tenant)
    value = subscription.plan.limits.get(module, DEFAULT_LIMITS.get(module, fallback))
    if not isinstance(value, int) or value < 0:
        return fallback
    return min(value, 100000)


def configured():
    return bool(settings.PAYNOW_INTEGRATION_ID and settings.PAYNOW_INTEGRATION_KEY and settings.PAYNOW_RESULT_URL)


def sign_fields(fields):
    material = ''.join(value for key, value in fields if key.lower() != 'hash') + settings.PAYNOW_INTEGRATION_KEY.strip().lower()
    return hashlib.sha512(material.encode('utf-8')).hexdigest().upper()


def verified_fields(raw):
    fields = parse_qsl(raw, keep_blank_values=True, strict_parsing=True, max_num_fields=40)
    keys = [key.lower() for key, _ in fields]
    if len(keys) != len(set(keys)) or 'hash' not in keys:
        raise ValueError('Missing or duplicate signature fields.')
    values = {key.lower(): value for key, value in fields}
    if not settings.PAYNOW_INTEGRATION_KEY or not hmac.compare_digest(sign_fields(fields), values['hash'].upper()):
        raise ValueError('Invalid payment signature.')
    return values


def provider_url(value):
    parts = urlsplit(value)
    if parts.scheme != 'https' or parts.hostname not in ('www.paynow.co.zw', 'paynow.co.zw') or parts.port not in (None, 443) or parts.username or parts.password:
        raise ValueError('Unexpected payment provider URL.')
    return value


def exchange(url, fields):
    provider_url(url)
    with httpx.Client(timeout=15, follow_redirects=False) as client:
        response = client.post(url, data=dict(fields))
        response.raise_for_status()
        raw = response.text
    if len(raw) > 10000:
        raise ValueError('Payment response is too large.')
    parsed = dict(parse_qsl(raw, keep_blank_values=True))
    if parsed.get('status', parsed.get('Status', '')).lower() == 'error':
        raise ValueError('Paynow rejected the request. Check merchant configuration and payment details.')
    return verified_fields(raw)


def initiate_payment(payment_id, email, phone=''):
    payment = BillingPayment.objects.select_related('plan').get(pk=payment_id)
    if payment.status != 'queued':
        return
    if not configured():
        raise ValueError('Paynow is not configured.')
    fields = [('resulturl', settings.PAYNOW_RESULT_URL), ('returnurl', f'{settings.FRONTEND_URL.rstrip("/")}/billing?payment={payment.pk}'),
              ('reference', payment.reference.hex), ('amount', f'{payment.amount:.2f}'), ('id', settings.PAYNOW_INTEGRATION_ID),
              ('additionalinfo', f'TeamFlow {payment.plan.name}: 30 days'), ('authemail', email), ('merchanttrace', payment.reference.hex)]
    url = 'https://www.paynow.co.zw/interface/initiatetransaction'
    if payment.method == 'ecocash':
        fields += [('phone', phone), ('method', 'ecocash')]
        url = 'https://www.paynow.co.zw/interface/remotetransaction'
    fields += [('status', 'Message')]
    fields += [('hash', sign_fields(fields))]
    # A timed-out initiation may have reached the provider. Do not retry a debit.
    payment.status = 'initiating'
    payment.save(update_fields=['status'])
    try:
        result = exchange(url, fields)
        payment.poll_url = provider_url(result['pollurl'])
        payment.checkout_url = provider_url(result['browserurl']) if result.get('browserurl') else ''
        payment.instructions = result.get('instructions', 'Follow the instructions on your phone to confirm the payment.') if payment.method == 'ecocash' else ''
        payment.status = 'pending'
        with transaction.atomic():
            current = BillingPayment.objects.select_for_update().get(pk=payment.pk)
            if current.granted_at:
                payment.status = current.status
                payment.granted_at, payment.period_end = current.granted_at, current.period_end
            payment.save()
    except Exception:
        payment.status = 'unknown'
        payment.instructions = 'The initiation result is uncertain. Do not pay again until this reference is checked with Paynow.'
        payment.save(update_fields=['status', 'instructions'])
        raise


def verify_payment(payment_id):
    payment = BillingPayment.objects.get(pk=payment_id)
    if not payment.poll_url:
        return
    result = exchange(payment.poll_url, [])
    try:
        amount = Decimal(result['amount'])
    except (KeyError, InvalidOperation):
        raise ValueError('Invalid payment amount.')
    if result.get('reference') != payment.reference.hex or not amount.is_finite() or amount != payment.amount:
        raise ValueError('Payment amount or reference does not match.')
    status = result.get('status', '').lower()
    if status not in ('paid', 'awaiting delivery', 'delivered', 'created', 'sent', 'cancelled', 'disputed', 'refunded'):
        raise ValueError('Unknown payment status.')
    with transaction.atomic():
        payment = BillingPayment.objects.select_for_update().select_related('plan', 'tenant').get(pk=payment.pk)
        subscription = subscription_for(payment.tenant)
        subscription = TenantSubscription.objects.select_for_update().get(pk=subscription.pk)
        payment.provider_reference = result.get('paynowreference', '')
        if status in ('paid', 'awaiting delivery', 'delivered'):
            if not payment.granted_at:
                start = timezone.now()
                if subscription.plan_id == payment.plan_id and subscription.status == 'active' and subscription.paid_until and subscription.paid_until > start:
                    start = subscription.paid_until
                payment.granted_at = timezone.now()
                payment.period_end = start + timedelta(days=30)
                subscription.plan = payment.plan
                subscription.paid_until = payment.period_end
                subscription.status = 'active'
                subscription.cancel_at_period_end = False
                subscription.save()
                audit(payment, payment.created_by, 'billing.activate', after={'plan': payment.plan_id, 'paid_until': payment.period_end.isoformat()})
            payment.status = 'paid'
            if subscription.plan_id == payment.plan_id and subscription.paid_until == payment.period_end and subscription.status == 'suspended':
                subscription.status = 'active'
                subscription.save(update_fields=['status'])
        elif status in ('refunded', 'disputed'):
            payment.status = status
            if payment.granted_at and subscription.plan_id == payment.plan_id and subscription.paid_until == payment.period_end:
                subscription.status = 'suspended'
                subscription.save(update_fields=['status'])
                audit(payment, payment.created_by, 'billing.suspend', after={'reason': status})
        elif not payment.granted_at:
            payment.status = 'cancelled' if status == 'cancelled' else 'pending'
        payment.save()


def payment_data(payment):
    return {'id': payment.pk, 'reference': payment.reference.hex, 'plan': payment.plan.name, 'amount': payment.amount, 'currency': payment.currency,
            'method': payment.method, 'status': payment.status, 'checkout_url': payment.checkout_url, 'instructions': payment.instructions, 'paid_until': payment.period_end}


class BillingView(APIView):
    def get(self, request):
        membership = workspace_membership(request)
        subscription = subscription_for(membership.tenant)
        payments = BillingPayment.objects.filter(tenant=membership.tenant).select_related('plan').order_by('-id')[:30] if can_admin_workspace(membership) else []
        return Response({'configured': configured(), 'plan': subscription.plan.name, 'status': subscription.status,
                         'paid_until': subscription.paid_until, 'cancel_at_period_end': subscription.cancel_at_period_end,
                         'trial_used': subscription.trial_used, 'trial_ends_at': subscription.trial_ends_at,
                         'limits': {**DEFAULT_LIMITS, **subscription.plan.limits}, 'plans': [{'id': p.pk, 'name': p.name, 'monthly_price': p.monthly_price, 'currency': p.currency, 'limits': {**DEFAULT_LIMITS, **p.limits}} for p in SaaSPlan.objects.filter(is_public=True)],
                         'payments': [payment_data(p) for p in payments], 'renewal': 'Customer-confirmed 30-day payments; no automatic debits.'})

    @transaction.atomic
    def patch(self, request):
        membership = workspace_membership(request)
        if not can_admin_workspace(membership):
            raise PermissionDenied('Workspace administrators only.')
        subscription = subscription_for(membership.tenant)
        subscription = TenantSubscription.objects.select_for_update().get(pk=subscription.pk)
        if request.data.get('action') == 'free':
            if subscription.plan.monthly_price > 0 and subscription.paid_until and subscription.paid_until > timezone.now() and subscription.status == 'active':
                subscription.cancel_at_period_end = True
            else:
                free = SaaSPlan.objects.filter(name='Free', monthly_price=0).first()
                if not free:
                    raise serializers.ValidationError('Configure a free plan first.')
                subscription.plan, subscription.status, subscription.paid_until = free, 'active', None
                subscription.cancel_at_period_end = False
        else:
            raise serializers.ValidationError('Unknown subscription action.')
        subscription.save()
        audit(subscription, request.user, 'billing.cancel')
        return self.get(request)


class TrialView(APIView):
    @transaction.atomic
    def post(self, request):
        from erp_foundation.models import Tenant
        membership = workspace_membership(request)
        if not can_admin_workspace(membership):
            raise PermissionDenied('Workspace administrators only.')
        Tenant.objects.select_for_update().get(pk=membership.tenant_id)
        subscription = subscription_for(membership.tenant)
        if subscription.trial_used or subscription.plan.monthly_price > 0:
            raise serializers.ValidationError('A trial is available once, from the free plan.')
        plan = get_object_or_404(SaaSPlan, pk=serializers.IntegerField(min_value=1).run_validation(request.data.get('plan')), is_public=True, monthly_price__gt=0)
        subscription.plan, subscription.status, subscription.trial_used = plan, 'trial', True
        subscription.trial_ends_at = timezone.now() + timedelta(days=settings.TRIAL_DAYS)
        subscription.save()
        audit(subscription, request.user, 'billing.trial', after={'plan': plan.pk, 'ends_at': subscription.trial_ends_at.isoformat()})
        return Response({'detail': 'Trial started.', 'trial_ends_at': subscription.trial_ends_at})


class CheckoutView(APIView):
    @transaction.atomic
    def post(self, request):
        membership = workspace_membership(request)
        if not can_admin_workspace(membership):
            raise PermissionDenied('Workspace administrators only.')
        if not configured():
            return Response({'detail': 'Configure your Paynow merchant ID, key and public result URL before accepting payments.'}, status=503)
        plan_id = serializers.IntegerField(min_value=1).run_validation(request.data.get('plan'))
        plan = get_object_or_404(SaaSPlan, pk=plan_id, is_public=True, monthly_price__gt=0, currency='USD')
        method = serializers.ChoiceField(choices=['paynow', 'ecocash']).run_validation(request.data.get('method', 'paynow'))
        phone = serializers.RegexField(r'^(?:0|\+?263)7\d{8}$').run_validation(request.data.get('phone')) if method == 'ecocash' else ''
        key = serializers.UUIDField().run_validation(request.data.get('request_key'))
        payment, created = BillingPayment.objects.get_or_create(request_key=key, defaults={'tenant': membership.tenant, 'created_by': request.user,
                          'plan': plan, 'amount': plan.monthly_price, 'currency': plan.currency, 'method': method})
        if payment.tenant_id != membership.tenant_id or payment.plan_id != plan.pk or payment.method != method:
            raise serializers.ValidationError('This request key belongs to another checkout.')
        if created:
            enqueue('billing_start', {'id': payment.pk, 'email': request.user.email, 'phone': phone}, f'billing-start:{payment.pk}')
            audit(payment, request.user, 'billing.checkout')
        return Response(payment_data(payment), status=202)


class PaymentStatusView(APIView):
    def get(self, request, pk):
        membership = workspace_membership(request)
        if not can_admin_workspace(membership):
            raise PermissionDenied('Workspace administrators only.')
        payment = get_object_or_404(BillingPayment, pk=pk, tenant=membership.tenant)
        return Response(payment_data(payment))


class PaynowResultView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = []

    @transaction.atomic
    def post(self, request):
        if len(request.body) > 10000:
            return Response(status=400)
        try:
            raw = request.body.decode('utf-8')
            values = verified_fields(raw)
            payment = BillingPayment.objects.select_for_update().get(reference=values.get('reference'))
            if Decimal(values.get('amount', 'NaN')) != payment.amount:
                raise ValueError('Amount mismatch.')
            if not payment.poll_url:
                payment.poll_url = provider_url(values['pollurl'])
                payment.save(update_fields=['poll_url'])
            digest = hashlib.sha512(raw.encode('utf-8')).hexdigest()
            _, created = BillingEvent.objects.get_or_create(digest=digest, defaults={'payment': payment, 'status': values.get('status', '')})
            if created:
                enqueue('billing_verify', {'id': payment.pk}, f'billing-verify:{digest}')
        except (ValueError, KeyError, UnicodeDecodeError, BillingPayment.DoesNotExist, InvalidOperation, serializers.ValidationError, DjangoValidationError):
            return Response({'detail': 'Invalid payment callback.'}, status=400)
        return Response(status=200)
