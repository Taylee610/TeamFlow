import json

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

from .models import Conversation
from .permissions import can_access_conversation


class ChatConsumer(AsyncWebsocketConsumer):
    """One socket per open conversation. Actual message *sending* still goes
    through the REST endpoint (single source of truth for auth/validation/
    attachments/canned-responses) -- this socket only pushes the result out
    to everyone else in the conversation in real time, plus lightweight
    typing indicators.
    """

    async def connect(self):
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.group_name = f"conversation_{self.conversation_id}"
        user = self.scope.get('user')

        if user is None or not user.is_authenticated:
            await self.close(code=4001)  # unauthenticated
            return

        if not await self._user_can_access(user):
            await self.close(code=4003)  # not a participant
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        if not await self._user_can_access(self.scope.get('user')):
            await self.close(code=4003)
            return
        try:
            data = json.loads(text_data)
        except (TypeError, ValueError):
            return

        if data.get('type') == 'typing':
            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type': 'typing_indicator',
                    'user_id': self.scope['user'].id,
                    'is_typing': bool(data.get('is_typing')),
                },
            )

    # --- handlers for events sent via channel_layer.group_send() ---

    async def chat_message(self, event):
        """Fired by the REST view (ConversationViewSet.messages) after a
        new message is saved."""
        if not await self._user_can_access(self.scope.get('user')):
            await self.close(code=4003)
            return
        await self.send(text_data=json.dumps({
            'kind': 'message',
            'message': event['message'],
        }))

    async def typing_indicator(self, event):
        if not await self._user_can_access(self.scope.get('user')):
            await self.close(code=4003)
            return
        if event['user_id'] == self.scope['user'].id:
            return  # don't echo back to the sender
        await self.send(text_data=json.dumps({
            'kind': 'typing',
            'user_id': event['user_id'],
            'is_typing': event['is_typing'],
        }))

    @database_sync_to_async
    def _user_can_access(self, user):
        conversation = Conversation.objects.filter(pk=self.conversation_id).first()
        if conversation is None:
            return False
        return can_access_conversation(user, conversation)
