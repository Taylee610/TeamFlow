"""Explicit workspace fixtures; global user roles never grant workspace access."""
from .models import Membership, Permission, Role
from .services import workspace_roles


def add_member(tenant, user, admin=False, manager=False):
    admin_role, member_role = workspace_roles(tenant)
    role = admin_role if admin else member_role
    if manager:
        role, _ = Role.objects.get_or_create(tenant=tenant, name='Project manager')
        permission, _ = Permission.objects.get_or_create(tenant=tenant, code='projects.manage', defaults={'module': 'projects'})
        role.permissions.add(permission)
    return Membership.objects.create(tenant=tenant, user=user, role=role)
