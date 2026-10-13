import http.client
import ipaddress
import socket
import time
import uuid
from datetime import timedelta
from urllib.parse import urlsplit
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from erp_foundation.models import AuditLog
from .models import Job, Monitor, MonitorCheck, NotificationPreference


def audit(record, user, action, before=None, after=None):
    AuditLog.objects.create(tenant=record.tenant, actor=user, action=action,
                            object_type=record._meta.label, object_id=str(record.pk),
                            before=before or {}, after=after or {})


def enqueue(kind, payload, dedup_key=None):
    return Job.objects.get_or_create(dedup_key=dedup_key or str(uuid.uuid4()), defaults={'kind': kind, 'payload': payload})[0]


def email_allowed(user):
    return not NotificationPreference.objects.filter(user=user, email_notifications=False).exists()


def probe(url):
    """Connect to a vetted IP, preserving TLS hostname verification; never follow redirects."""
    from .serializers import safe_url
    safe_url(url)
    parts = urlsplit(url)
    port = parts.port or (443 if parts.scheme == 'https' else 80)
    addresses = socket.getaddrinfo(parts.hostname, port, type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(row[4][0]).is_global for row in addresses):
        raise ValueError('Only public internet addresses can be monitored.')
    pinned_address = addresses[0][4][0]
    connection_type = http.client.HTTPSConnection if parts.scheme == 'https' else http.client.HTTPConnection
    connection = connection_type(parts.hostname, port=port, timeout=10)
    # HTTPSConnection still performs TLS verification against parts.hostname.
    connection._create_connection = lambda address, timeout, source_address=None: socket.create_connection((pinned_address, port), timeout, source_address)
    started = time.monotonic()
    try:
        path = parts.path or '/'
        if parts.query:
            path += '?' + parts.query
        connection.request('GET', path, headers={'User-Agent': 'TeamFlow-Monitor/1.0', 'Connection': 'close'})
        response = connection.getresponse()
        return 200 <= response.status < 400, response.status, round((time.monotonic() - started) * 1000), ''
    finally:
        connection.close()


def check_monitor(monitor_id, expected_url=None):
    monitor = Monitor.objects.filter(pk=monitor_id, enabled=True, tenant__is_active=True).first()
    if not monitor or (expected_url and expected_url != monitor.url):
        return
    from .billing import active_subscription
    from rest_framework.exceptions import PermissionDenied
    try:
        active_subscription(monitor.tenant)
    except PermissionDenied:
        return
    checked_url = monitor.url
    try:
        up, status_code, latency, error = probe(checked_url)
    except Exception as exc:
        up, status_code, latency, error = False, None, 0, str(exc)[:300]
    with transaction.atomic():
        monitor = Monitor.objects.select_for_update().get(pk=monitor_id)
        if not monitor.enabled or monitor.url != checked_url or not monitor.tenant.is_active:
            return
        now = timezone.now()
        check = MonitorCheck.objects.create(monitor=monitor, is_up=up, status_code=status_code, latency_ms=latency, error=error, checked_at=now)
        old_state = monitor.state
        monitor.state = 'up' if up else 'down'
        monitor.last_checked_at = now
        monitor.next_check_at = now + timedelta(minutes=monitor.interval_minutes)
        if not up and old_state != 'down':
            monitor.incident_started_at = now
        elif up:
            monitor.incident_started_at = None
        monitor.save()
        from erp_foundation.access import active_memberships
        if monitor.state != old_state and (not up or old_state == 'down') and email_allowed(monitor.created_by) and active_memberships(monitor.created_by).filter(tenant=monitor.tenant).exists():
            enqueue('email', {'to': monitor.created_by.email, 'subject': f'{monitor.name}: {monitor.state}',
                             'guard_user': monitor.created_by_id, 'guard_tenant': monitor.tenant_id,
                             'body': f'{monitor.url}\nState: {monitor.state}\nChecked: {now.isoformat()}\n{error}'}, f'monitor-alert:{check.pk}')


def schedule_monitors():
    now = timezone.now()
    for pk in Monitor.objects.filter(enabled=True, tenant__is_active=True, next_check_at__lte=now).values_list('pk', flat=True)[:100]:
        with transaction.atomic():
            monitor = Monitor.objects.select_for_update().get(pk=pk)
            if not monitor.enabled or monitor.next_check_at > now:
                continue
            enqueue('monitor', {'id': pk, 'url': monitor.url}, f'monitor:{pk}:{monitor.next_check_at.isoformat()}')
            monitor.next_check_at = now + timedelta(minutes=monitor.interval_minutes)
            monitor.save(update_fields=['next_check_at'])


def claim_job():
    now = timezone.now()
    candidates = Job.objects.filter(Q(status='pending', available_at__lte=now) | Q(status='running', locked_until__lte=now)).order_by('available_at', 'pk')
    for job in candidates[:20]:
        lease = uuid.uuid4()
        changed = Job.objects.filter(pk=job.pk).filter(Q(status='pending', available_at__lte=now) | Q(status='running', locked_until__lte=now)).update(
            status='running', locked_until=now + timedelta(minutes=5), lease=lease, attempts=job.attempts + 1)
        if changed:
            return Job.objects.get(pk=job.pk, lease=lease)
    return None


def execute_job(job):
    if job.kind == 'monitor':
        check_monitor(job.payload['id'], job.payload.get('url'))
    elif job.kind == 'billing_start':
        from .billing import initiate_payment
        initiate_payment(job.payload['id'], job.payload['email'], job.payload.get('phone', ''))
    elif job.kind == 'billing_verify':
        from .billing import verify_payment
        verify_payment(job.payload['id'])
    elif job.kind == 'email':
        if job.payload.get('guard_user'):
            from accounts.models import User
            from erp_foundation.access import active_memberships
            user = User.objects.filter(pk=job.payload['guard_user'], is_active=True).first()
            if not user or not email_allowed(user) or not active_memberships(user).filter(tenant_id=job.payload.get('guard_tenant')).exists():
                return
        send_mail(job.payload['subject'], job.payload['body'], None, [job.payload['to']], fail_silently=False)
    elif job.kind in ('task_assigned', 'task_reminder'):
        from projects.models import Task
        from accounts.models import User
        from erp_foundation.access import active_memberships
        from notifications.emails import send_task_assigned_email, send_due_date_reminder_email
        task = Task.objects.select_related('assigned_to', 'project').filter(pk=job.payload['task']).first()
        if not task or not task.assigned_to or task.assigned_to_id != job.payload.get('assignee') or not email_allowed(task.assigned_to) or not active_memberships(task.assigned_to).filter(tenant_id=task.project.tenant_id).exists():
            return
        if job.kind == 'task_assigned':
            assigner = User.objects.filter(pk=job.payload.get('assigned_by')).first()
            send_task_assigned_email(task, assigned_by=assigner)
        elif task.status != Task.DONE:
            send_due_date_reminder_email(task)
    else:
        raise ValueError('Unknown job type.')


def run_one():
    job = claim_job()
    if not job:
        return False
    try:
        execute_job(job)
        Job.objects.filter(pk=job.pk, lease=job.lease).update(status='done', locked_until=None, last_error='')
    except Exception as exc:
        Job.objects.filter(pk=job.pk, lease=job.lease).update(status='failed' if job.attempts >= 5 else 'pending',
            available_at=timezone.now() + timedelta(seconds=min(3600, 30 * 2 ** job.attempts)), locked_until=None, last_error=str(exc)[:1000])
    return True
