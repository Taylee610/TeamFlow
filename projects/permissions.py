# projects/permissions.py
from rest_framework import permissions

class IsAssigneeOrProjectOwnerOrReadOnly(permissions.BasePermission):
    """
    - Read-only -> allowed to any authenticated user (we will restrict querysets elsewhere).
    - Update (PUT/PATCH) -> allowed if request.user == assigned_to, is the project owner,
      or is a member of the project (so any teammate can move cards on the kanban board).
    - Destroy (DELETE) -> only if request.user == project.owner.
    """

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True

        if view.action in ('update', 'partial_update'):
            return (
                obj.assigned_to == request.user
                or obj.project.owner == request.user
                or obj.project.members.filter(pk=request.user.pk).exists()
            )

        if view.action == 'destroy':
            return obj.project.owner == request.user

        return False