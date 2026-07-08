from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import Conversation, ConversationParticipant, CannedResponse
from .serializers import (
    ConversationSerializer, ConversationCreateSerializer,
    MessageSerializer, MessageCreateSerializer, CannedResponseSerializer,
)
from .permissions import IsConversationParticipant


class ConversationViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, IsConversationParticipant]
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

    def get_serializer_class(self):
        if self.action == 'create':
            return ConversationCreateSerializer
        return ConversationSerializer

    def get_queryset(self):
        user = self.request.user
        # Channels/DMs you're a participant of, plus every support
        # conversation (any authenticated user can pick those up for now).
        return Conversation.objects.filter(
            Q(participants__user=user) | Q(type=Conversation.SUPPORT)
        ).distinct()

    def create(self, request, *args, **kwargs):
        serializer = ConversationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = request.user

        if data['type'] == Conversation.CHANNEL:
            if not data.get('name'):
                raise ValidationError({'name': 'A channel needs a name.'})
            conversation = Conversation.objects.create(
                type=Conversation.CHANNEL,
                name=data['name'],
                project=data.get('project'),
                is_private=data.get('is_private', False),
            )
            member_ids = set(data.get('member_ids', [])) | {user.id}
            for uid in member_ids:
                ConversationParticipant.objects.get_or_create(conversation=conversation, user_id=uid)

        else:  # Conversation.DM
            member_ids = data.get('member_ids', [])
            if len(member_ids) != 1:
                raise ValidationError({'member_ids': 'A direct message needs exactly one other member.'})
            other_id = member_ids[0]
            if other_id == user.id:
                raise ValidationError({'member_ids': "You can't start a DM with yourself."})

            existing = (
                Conversation.objects.filter(type=Conversation.DM, participants__user=user)
                .filter(participants__user_id=other_id)
                .first()
            )
            conversation = existing or Conversation.objects.create(type=Conversation.DM)
            if not existing:
                ConversationParticipant.objects.create(conversation=conversation, user=user)
                ConversationParticipant.objects.create(conversation=conversation, user_id=other_id)

        out = ConversationSerializer(conversation, context={'request': request})
        return Response(out.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='read')
    def mark_read(self, request, pk=None):
        conversation = self.get_object()
        participant, _ = ConversationParticipant.objects.get_or_create(
            conversation=conversation, user=request.user
        )
        participant.last_read_at = timezone.now()
        participant.save(update_fields=['last_read_at'])
        return Response({'last_read_at': participant.last_read_at})

    @action(detail=True, methods=['get', 'post'], url_path='messages')
    def messages(self, request, pk=None):
        conversation = self.get_object()

        if request.method == 'GET':
            qs = conversation.messages.select_related('sender', 'sender_contact').prefetch_related('reactions')
            page = self.paginate_queryset(qs)
            serializer = MessageSerializer(page if page is not None else qs, many=True)
            if page is not None:
                return self.get_paginated_response(serializer.data)
            return Response(serializer.data)

        serializer = MessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = serializer.save(conversation=conversation, sender=request.user)

        Conversation.objects.filter(pk=conversation.pk).update(updated_at=timezone.now())
        self._broadcast_message(message)

        return Response(MessageSerializer(message).data, status=status.HTTP_201_CREATED)

    def _broadcast_message(self, message):
        try:
            channel_layer = get_channel_layer()
            if channel_layer is None:
                return
            group_name = f"conversation_{message.conversation_id}"
            async_to_sync(channel_layer.group_send)(
                group_name,
                {
                    'type': 'chat_message',
                    'message': MessageSerializer(message).data,
                },
            )
        except Exception:
            pass


class CannedResponseViewSet(viewsets.ModelViewSet):
    serializer_class = CannedResponseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return CannedResponse.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)