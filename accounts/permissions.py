from rest_framework import permissions
from erp_foundation.access import active_memberships, can_admin_workspace


class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        from erp_foundation.access import workspace_membership
        return request.user.is_authenticated and can_admin_workspace(workspace_membership(request))


def project_membership(user, project):
    if not user or not user.is_authenticated or not project.tenant_id:
        return None
    return active_memberships(user).filter(tenant_id=project.tenant_id).first()


def can_view_project(user, project):
    membership = project_membership(user, project)
    return bool(membership and (can_admin_workspace(membership) or project.owner_id == user.pk
                                or project.members.filter(pk=user.pk).exists()))


def can_manage_project(user, project):
    membership = project_membership(user, project)
    return bool(membership and (can_admin_workspace(membership) or project.owner_id == user.pk
                                or (membership.has_permission('projects.manage') and project.members.filter(pk=user.pk).exists())))
