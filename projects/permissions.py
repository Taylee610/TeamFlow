# projects/permissions.py
from rest_framework import permissions

class IsAssigneeOrProjectOwnerOrReadOnly(permissions.BasePermission):
    """
    - Read-only -> allowed to any authenticated user (we will restrict querysets elsewhere).
    - Update (PUT/PATCH) -> only if request.user == assigned_to.
    - Destroy (DELETE) -> only if request.user == project.owner.
    """

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True

        
        if view.action in ('update', 'partial_update'):
            return obj.assigned_to == request.user

        
        if view.action == 'destroy':
            return obj.project.owner == request.user

        
        return False
