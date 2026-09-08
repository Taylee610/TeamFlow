from django.db import transaction
from django.utils.text import slugify
from uuid import uuid4

from .models import Tenant, Role, Permission, Membership


def workspace_roles(tenant):
    permission, _ = Permission.objects.get_or_create(
        tenant=tenant, code='workspace.manage', defaults={'module': 'workspace'},
    )
    admin, _ = Role.objects.get_or_create(tenant=tenant, name='Workspace admin')
    admin.permissions.add(permission)
    member, _ = Role.objects.get_or_create(tenant=tenant, name='Workspace member')
    return admin, member


@transaction.atomic
def create_workspace(user, name):
    tenant = Tenant.objects.create(name=name, slug=f'{slugify(name)[:16] or "workspace"}-{uuid4().hex}')
    admin, _ = workspace_roles(tenant)
    Membership.objects.create(tenant=tenant, user=user, role=admin)
    return tenant
