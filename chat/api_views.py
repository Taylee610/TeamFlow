from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction
from erp_foundation.access import workspace_membership, can_admin_workspace, active_memberships
from accounts.permissions import can_view_project
from rest_framework.exceptions import PermissionDenied
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import Conversation, ConversationParticipant, CannedResponse
from .serializers import (
    ConversationSerializer, ConversationCreateSerializer,
    MessageSerializer, MessageCreateSerializer, CannedResponseSerializer,
)
from .permissions import IsConversationParticipant

User = get_user_model()


class ConversationViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, IsConversationParticipant]
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

    def get_serializer_class(self):
        if self.action == 'create':
            return ConversationCreateSerializer
        return ConversationSerializer

    def get_queryset(self):
        user = self.request.user
        membership = workspace_membership(self.request)
        support = Q(type=Conversation.SUPPORT)
        if not can_admin_workspace(membership):
            support &= Q(assigned_agent=user)
        return Conversation.objects.filter(tenant=membership.tenant).filter(
            (Q(participants__user=user) & ~Q(type=Conversation.SUPPORT)) | support
        ).distinct()

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = ConversationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = request.user
        membership = workspace_membership(request)
        member_ids = set(data.get('member_ids', []))
        valid_ids = set(User.objects.filter(
            id__in=member_ids, is_active=True, tenant_memberships__tenant=membership.tenant,
            tenant_memberships__is_active=True, tenant_memberships__role__tenant=membership.tenant,
        ).values_list('id', flat=True))
        if valid_ids != member_ids:
            raise ValidationError({'member_ids': 'Choose active members of this workspace.'})
        project = data.get('project')
        if project and (project.tenant_id != membership.tenant_id or not can_view_project(user, project)):
            raise ValidationError({'project': 'Project is not available in this workspace.'})

        if data['type'] == Conversation.CHANNEL:
            if not data.get('name'):
                raise ValidationError({'name': 'A channel needs a name.'})
            conversation = Conversation.objects.create(
                tenant=membership.tenant,
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
                Conversation.objects.filter(tenant=membership.tenant, type=Conversation.DM, participants__user=user)
                .filter(participants__user_id=other_id)
                .first()
            )
            conversation = existing or Conversation.objects.create(tenant=membership.tenant, type=Conversation.DM)
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

    @action(detail=False, methods=['get'], url_path='my')
    def my(self, request):
        """Support conversations assigned to the current agent."""
        qs = self.get_queryset().filter(type=Conversation.SUPPORT, assigned_agent=request.user)
        return Response(ConversationSerializer(qs, many=True, context={'request': request}).data)

    @action(detail=False, methods=['get'], url_path='unassigned')
    def unassigned(self, request):
        """Support conversations nobody has picked up yet."""
        qs = self.get_queryset().filter(type=Conversation.SUPPORT, assigned_agent__isnull=True)
        return Response(ConversationSerializer(qs, many=True, context={'request': request}).data)

    @action(detail=True, methods=['post'], url_path='assign')
    def assign(self, request, pk=None):
        """Assign a support conversation to an agent (defaults to self)."""
        conversation = self.get_object()
        if conversation.type != Conversation.SUPPORT:
            raise ValidationError('Only support conversations can be assigned.')
        if not can_admin_workspace(workspace_membership(request)):
            raise PermissionDenied('Only workspace administrators can assign support conversations.')

        agent_id = request.data.get('agent_id')
        agent = get_object_or_404(User, pk=agent_id) if agent_id else request.user
        if not active_memberships(agent).filter(tenant_id=conversation.tenant_id).exists():
            raise ValidationError({'agent_id': 'Choose an active member of this workspace.'})

        conversation.assigned_agent = agent
        conversation.save(update_fields=['assigned_agent', 'updated_at'])
        return Response(ConversationSerializer(conversation, context={'request': request}).data)

    @action(detail=True, methods=['get', 'post'], url_path='messages')
    @transaction.atomic
    def messages(self, request, pk=None):
        conversation = self.get_object()

        if request.method == 'GET':
            qs = conversation.messages.select_related('sender', 'sender_contact').prefetch_related('reactions')
            page = self.paginate_queryset(qs)
            serializer = MessageSerializer(page if page is not None else qs, many=True)
            if page is not None:
                return self.get_paginated_response(serializer.data)
            return Response(serializer.data)

        serializer = MessageCreateSerializer(data=request.data, context={'conversation': conversation})
        serializer.is_valid(raise_exception=True)
        from workspace_tools.quotas import enforce_upload_limit
        enforce_upload_limit(conversation.tenant, serializer.validated_data.get('attachment'))
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
