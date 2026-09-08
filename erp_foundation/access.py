"""Shared, fail-closed workspace resolution for HTTP and realtime callers."""
from django.db.models import F
from rest_framework.exceptions import PermissionDenied, ValidationError

from .models import Membership


def active_memberships(user):
    return Membership.objects.select_related('tenant', 'role').filter(
        user=user, user__is_active=True, is_active=True, tenant__is_active=True,
        role__tenant_id=F('tenant_id'),
    )


def workspace_membership(request):
    if hasattr(request, '_workspace_membership'):
        return request._workspace_membership
    memberships = active_memberships(request.user)
    tenant_id = request.headers.get('X-Workspace-ID')
    if tenant_id:
        if not tenant_id.isdecimal():
            raise ValidationError({'workspace': 'Invalid workspace ID.'})
        membership = memberships.filter(tenant_id=tenant_id).first()
    else:
        candidates = list(memberships[:2])
        if len(candidates) > 1:
            raise ValidationError({'workspace': 'Select a workspace using X-Workspace-ID.'})
        membership = candidates[0] if candidates else None
    if membership is None:
        raise PermissionDenied('No active membership in this workspace.')
    request._workspace_membership = membership
    return membership


def can_admin_workspace(membership):
    return membership.has_permission('workspace.manage')
