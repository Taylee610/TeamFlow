from rest_framework import permissions
from erp_foundation.access import active_memberships, can_admin_workspace


def can_access_conversation(user, conversation):
    if not user or not user.is_authenticated or not conversation.tenant_id:
        return False
    membership = active_memberships(user).filter(tenant_id=conversation.tenant_id).first()
    if not membership:
        return False
    if conversation.type == conversation.SUPPORT:
        return can_admin_workspace(membership) or conversation.assigned_agent_id == user.pk
    return conversation.participants.filter(user=user).exists()


class IsConversationParticipant(permissions.BasePermission):
    """
    - Channels/DMs -> only participants can read or write.
    - Support conversations -> any authenticated user can act as an agent
      for now (no dedicated "agent" role yet -- refine when that's added).
    """

    def has_object_permission(self, request, view, obj):
        conversation = obj if hasattr(obj, 'type') else obj.conversation

        return can_access_conversation(request.user, conversation)
