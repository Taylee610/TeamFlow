from rest_framework import permissions


class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_admin)


def can_manage_project(user, project):
    """Owner-equivalent rights: the real owner, an org Admin, or a Manager
    who is a member of the project.
    """
    if project.owner_id == user.id:
        return True
    if user.is_admin:
        return True
    if user.role == user.Role.MANAGER and project.members.filter(pk=user.pk).exists():
        return True
    return False
