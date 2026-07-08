from rest_framework import permissions


class IsConversationParticipant(permissions.BasePermission):
    """
    - Channels/DMs -> only participants can read or write.
    - Support conversations -> any authenticated user can act as an agent
      for now (no dedicated "agent" role yet -- refine when that's added).
    """

    def has_object_permission(self, request, view, obj):
        conversation = obj if hasattr(obj, 'type') else obj.conversation

        if conversation.type == conversation.SUPPORT:
            return True

        return conversation.participants.filter(user=request.user).exists()