from django.contrib import admin
from .models import Contact, Conversation, ConversationParticipant, CannedResponse, Message, MessageReaction


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'email', 'external_id', 'last_seen_at')
    search_fields = ('name', 'email', 'external_id')


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'type', 'project', 'status', 'assigned_agent', 'updated_at')
    list_filter = ('type', 'status', 'is_private')


@admin.register(ConversationParticipant)
class ConversationParticipantAdmin(admin.ModelAdmin):
    list_display = ('conversation', 'user', 'joined_at', 'last_read_at')


@admin.register(CannedResponse)
class CannedResponseAdmin(admin.ModelAdmin):
    list_display = ('shortcut', 'owner', 'created_at')


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'conversation', 'created_at')
    list_filter = ('conversation__type',)


@admin.register(MessageReaction)
class MessageReactionAdmin(admin.ModelAdmin):
    list_display = ('message', 'user', 'emoji')