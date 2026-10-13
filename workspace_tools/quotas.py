from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import serializers
from erp_foundation.models import Tenant, Membership
from .models import UsageCounter
from .billing import limit_for, active_subscription


@transaction.atomic
def reserve_ai_request(tenant):
    Tenant.objects.select_for_update().get(pk=tenant.pk)
    maximum = limit_for(tenant, 'ai', 20)
    period = timezone.now().strftime('%Y-%m')
    usage, _ = UsageCounter.objects.get_or_create(tenant=tenant, module='ai', period=period)
    if usage.count >= maximum:
        raise serializers.ValidationError('This workspace has reached its monthly AI request limit.')
    usage.count += 1
    usage.save(update_fields=['count'])


def ensure_seat(tenant, member=None):
    # Caller holds the workspace row lock until membership is committed.
    if member and member.is_active:
        return
    maximum = limit_for(tenant, 'seats', 20)
    seats = Membership.objects.filter(tenant=tenant, is_active=True, user__is_active=True).count()
    if seats >= maximum:
        raise serializers.ValidationError('This workspace has reached its active member limit.')


def stored_bytes(tenant):
    from projects.models import Task
    from chat.models import Message
    from .models import ApprovalFile, ApprovalVersion
    total = 0
    files = []
    for queryset, name in [(Task.objects.filter(project__tenant=tenant).exclude(attachment=''), 'attachment'),
                            (Message.objects.filter(conversation__tenant=tenant).exclude(attachment=''), 'attachment'),
                            (ApprovalFile.objects.filter(tenant=tenant), 'file'),
                            (ApprovalVersion.objects.filter(approval__tenant=tenant), 'file')]:
        for record in queryset.only(name):
            file = getattr(record, name)
            if file:
                files.append(file)
    # Count files that still exist, including replaced versions retained on disk
    # only while they remain referenced by a record. See retention notes.
    counted = set()
    for file in files:
        if file.name in counted:
            continue
        counted.add(file.name)
        try:
            total += file.size
        except FileNotFoundError:
            continue
        except OSError:
            raise serializers.ValidationError('Storage is unavailable. Retry the upload later.')
    return total


def enforce_upload_limit(tenant, uploaded):
    if not uploaded:
        return
    Tenant.objects.select_for_update().get(pk=tenant.pk)
    if uploaded.size > 20 * 1024 * 1024:
        raise serializers.ValidationError('Files must be at most 20 MB.')
    maximum = limit_for(tenant, 'storage_mb', 100) * 1024 * 1024
    if stored_bytes(tenant) + uploaded.size > maximum:
        raise serializers.ValidationError('This workspace has reached its attachment storage limit.')
