from django.conf import settings
from django.db import models


class Contact(models.Model):
    """An external, non-authenticated person reaching in via the live-chat
    widget (customer support side of the house). Not a User -- contacts
    never log into TeamFlow itself."""
    name = models.CharField(max_length=120, blank=True)
    email = models.EmailField(blank=True)
    external_id = models.CharField(
        max_length=64, unique=True,
        help_text="Anonymous visitor id set by the embeddable widget (cookie/localStorage id).",
    )
    first_seen_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name or self.email or self.external_id


class Conversation(models.Model):
    tenant = models.ForeignKey('erp_foundation.Tenant', on_delete=models.PROTECT, null=True, blank=True, related_name='conversations')
    CHANNEL = 'channel'
    DM = 'dm'
    SUPPORT = 'support'
    TYPE_CHOICES = [
        (CHANNEL, 'Channel'),
        (DM, 'Direct message'),
        (SUPPORT, 'Support conversation'),
    ]

    OPEN = 'open'
    PENDING = 'pending'
    RESOLVED = 'resolved'
    STATUS_CHOICES = [
        (OPEN, 'Open'),
        (PENDING, 'Pending'),
        (RESOLVED, 'Resolved'),
    ]

    type = models.CharField(max_length=10, choices=TYPE_CHOICES)

    # Channels only: a display name and optional project scope + privacy.
    name = models.CharField(max_length=100, blank=True)
    project = models.ForeignKey(
        'projects.Project', on_delete=models.CASCADE,
        null=True, blank=True, related_name='conversations',
        help_text="Set for project channels. Null for workspace-wide channels, DMs, and support.",
    )
    is_private = models.BooleanField(default=False)

    # Support conversations only.
    contact = models.ForeignKey(
        Contact, on_delete=models.CASCADE,
        null=True, blank=True, related_name='conversations',
    )
    assigned_agent = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='assigned_support_conversations',
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=OPEN)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        if self.type == self.CHANNEL:
            return f"#{self.name}"
        if self.type == self.SUPPORT:
            return f"Support: {self.contact}"
        return f"DM #{self.pk}"


class ConversationParticipant(models.Model):
    """Links a User to a channel or DM. Support conversations use
    assigned_agent instead, since the other side is a Contact, not a User."""
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='participants')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='chat_participations')
    last_read_at = models.DateTimeField(null=True, blank=True)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('conversation', 'user')


class CannedResponse(models.Model):
    """A reusable saved reply a user can insert with one click,
    for repetitive support replies or internal status updates."""
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='canned_responses')
    shortcut = models.CharField(max_length=40, help_text="e.g. 'thanks' -- typed after / to trigger it.")
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('owner', 'shortcut')

    def __str__(self):
        return f"/{self.shortcut}"


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')

    # Exactly one of these is set, depending on who sent it.
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='chat_messages',
    )
    sender_contact = models.ForeignKey(
        Contact, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='messages',
    )

    body = models.TextField(blank=True)
    attachment = models.FileField(upload_to='chat_files/', blank=True, null=True)

    # Simple thread support: replies point back at the parent message.
    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE,
        null=True, blank=True, related_name='replies',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    edited_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        who = self.sender or self.sender_contact or 'unknown'
        return f"{who}: {self.body[:40]}"


class MessageReaction(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='chat_reactions')
    emoji = models.CharField(max_length=8)

    class Meta:
        unique_together = ('message', 'user', 'emoji')
