from rest_framework import serializers
from projects.models import Project
from projects.serializers import UserSerializer
from .models import Contact, Conversation, ConversationParticipant, CannedResponse, Message, MessageReaction


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ['id', 'name', 'email', 'external_id', 'first_seen_at', 'last_seen_at']
        read_only_fields = ['first_seen_at', 'last_seen_at']


class MessageReactionSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = MessageReaction
        fields = ['id', 'emoji', 'user']


class MessageSerializer(serializers.ModelSerializer):
    """Output shape for a message -- used for history and broadcasts."""
    sender = UserSerializer(read_only=True)
    sender_contact = ContactSerializer(read_only=True)
    reactions = MessageReactionSerializer(many=True, read_only=True)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.attachment:
            data['attachment'] = f'/files/messages/{instance.pk}/'
        return data

    class Meta:
        model = Message
        fields = [
            'id', 'conversation', 'sender', 'sender_contact', 'body',
            'attachment', 'parent', 'reactions', 'created_at', 'edited_at',
        ]
        read_only_fields = fields


class MessageCreateSerializer(serializers.ModelSerializer):
    """Input shape for posting a new message. conversation/sender are set
    by the view, not the client."""
    attachment = serializers.FileField(required=False, allow_null=True)

    class Meta:
        model = Message
        fields = ['body', 'attachment', 'parent']

    def validate(self, attrs):
        parent = attrs.get('parent')
        conversation = self.context.get('conversation')
        if parent and (not conversation or parent.conversation_id != conversation.pk):
            raise serializers.ValidationError({'parent': 'Replies must belong to this conversation.'})
        if not attrs.get('body') and not attrs.get('attachment'):
            raise serializers.ValidationError('A message needs text or an attachment.')
        return attrs


class ConversationParticipantSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = ConversationParticipant
        fields = ['id', 'user', 'last_read_at', 'joined_at']


class ConversationSerializer(serializers.ModelSerializer):
    """Output shape -- read-only, used for list/retrieve/create responses."""
    participants = ConversationParticipantSerializer(many=True, read_only=True)
    contact = ContactSerializer(read_only=True)
    assigned_agent = UserSerializer(read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True, default=None)
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            'id', 'type', 'name', 'project', 'project_name', 'is_private',
            'contact', 'assigned_agent', 'status', 'participants',
            'last_message', 'unread_count', 'created_at', 'updated_at',
        ]
        read_only_fields = ['type', 'project']

    def get_last_message(self, obj):
        msg = obj.messages.order_by('-created_at').first()
        if not msg:
            return None
        sender_name = None
        if msg.sender:
            sender_name = msg.sender.first_name or msg.sender.email
        elif msg.sender_contact:
            sender_name = str(msg.sender_contact)
        return {'body': msg.body, 'created_at': msg.created_at, 'sender_name': sender_name}

    def get_unread_count(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return 0
        participant = obj.participants.filter(user=request.user).first()
        qs = obj.messages.all()
        if participant and participant.last_read_at:
            qs = qs.filter(created_at__gt=participant.last_read_at)
        return qs.count()


class ConversationCreateSerializer(serializers.Serializer):
    """Input shape for creating a channel or a DM. Support conversations are
    created from the widget-facing endpoint instead (a later piece)."""
    type = serializers.ChoiceField(choices=[Conversation.CHANNEL, Conversation.DM])
    name = serializers.CharField(required=False, allow_blank=True, default='')
    project = serializers.PrimaryKeyRelatedField(queryset=Project.objects.all(), required=False, allow_null=True)
    is_private = serializers.BooleanField(required=False, default=False)
    member_ids = serializers.ListField(child=serializers.IntegerField(), required=False, default=list)


class CannedResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = CannedResponse
        fields = ['id', 'shortcut', 'body', 'created_at']
        read_only_fields = ['created_at']
