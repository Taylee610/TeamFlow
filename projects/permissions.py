# projects/permissions.py
from rest_framework import permissions

from accounts.permissions import can_manage_project


class IsAssigneeOrProjectOwnerOrReadOnly(permissions.BasePermission):
    """
    - Read-only -> allowed to any authenticated user (we will restrict querysets elsewhere).
    - Update (PUT/PATCH) -> allowed if request.user == assigned_to, is the project owner,
      or is a member of the project (so any teammate can move cards on the kanban board).
    - Destroy (DELETE) -> only if the user can manage the project (owner, org Admin, or a
      Manager who is a member of the project).
    """

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True

        if view.action in ('update', 'partial_update'):
            return (
                can_manage_project(request.user, obj.project)
                or obj.project.members.filter(pk=request.user.pk).exists()
            )

        if view.action == 'destroy':
            return can_manage_project(request.user, obj.project)

        return False


class IsProjectManagerOrReadOnly(permissions.BasePermission):
    """
    - Read-only -> allowed (queryset already restricts to owner/members/admin).
    - Write (update/partial_update/destroy) -> only if the user can manage the
      project (owner, org Admin, or a Manager who is a member of the project).
    """

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return can_manage_project(request.user, obj)
