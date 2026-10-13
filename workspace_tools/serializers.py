from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from rest_framework import serializers
from erp_foundation.access import workspace_membership, can_admin_workspace, active_memberships
from accounts.permissions import can_view_project
from . import models


def safe_url(value):
    parts = urlsplit(value)
    if parts.scheme not in ('http', 'https') or not parts.hostname or parts.username or parts.password:
        raise serializers.ValidationError('Use an HTTP or HTTPS URL without embedded credentials.')
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise serializers.ValidationError('Invalid URL characters.')
    try:
        if parts.port and parts.port not in (80, 443):
            raise serializers.ValidationError('Only ports 80 and 443 are supported.')
    except ValueError:
        raise serializers.ValidationError('Invalid port.')
    return value


class WorkspaceSerializer(serializers.ModelSerializer):
    class Meta:
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']

    def workspace(self):
        return workspace_membership(self.context['request']).tenant


class MonitorSerializer(WorkspaceSerializer):
    class Meta(WorkspaceSerializer.Meta):
        model = models.Monitor
        fields = ['id', 'name', 'url', 'interval_minutes', 'enabled', 'state', 'last_checked_at', 'incident_started_at', 'created_by']
        read_only_fields = WorkspaceSerializer.Meta.read_only_fields + ['state', 'last_checked_at', 'incident_started_at']

    validate_url = staticmethod(safe_url)

    def validate_interval_minutes(self, value):
        if not 5 <= value <= 1440:
            raise serializers.ValidationError('Choose an interval between 5 and 1440 minutes.')
        return value


class ClientSerializer(WorkspaceSerializer):
    class Meta(WorkspaceSerializer.Meta):
        model = models.Client
        fields = ['id', 'name', 'email', 'phone', 'company', 'stage', 'notes', 'projects', 'created_by']

    def validate_projects(self, projects):
        user = self.context['request'].user
        if any(p.tenant_id != self.workspace().pk or not can_view_project(user, p) for p in projects):
            raise serializers.ValidationError('Choose projects you can access in this workspace.')
        return projects


class LinkProfileSerializer(WorkspaceSerializer):
    class Meta(WorkspaceSerializer.Meta):
        model = models.LinkProfile
        fields = ['id', 'slug', 'title', 'bio', 'theme', 'links', 'published', 'created_by']

    def validate_links(self, links):
        if not isinstance(links, list) or len(links) > 30:
            raise serializers.ValidationError('Provide up to 30 links.')
        clean = []
        for link in links:
            if not isinstance(link, dict) or not isinstance(link.get('label'), str) or not link['label'].strip() or len(link['label']) > 100:
                raise serializers.ValidationError('Each link needs a label of up to 100 characters.')
            if not isinstance(link.get('url'), str) or len(link['url']) > 1000:
                raise serializers.ValidationError('Each link needs a URL of up to 1000 characters.')
            clean.append({'label': link['label'].strip(), 'url': safe_url(link['url'])})
        return clean


class HabitSerializer(WorkspaceSerializer):
    class Meta(WorkspaceSerializer.Meta):
        model = models.Habit
        fields = ['id', 'name', 'timezone', 'archived', 'created_by']

    def validate_timezone(self, value):
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise serializers.ValidationError('Choose a valid IANA timezone.')
        return value


class DeckSerializer(WorkspaceSerializer):
    card_count = serializers.IntegerField(read_only=True)

    class Meta(WorkspaceSerializer.Meta):
        model = models.Deck
        fields = ['id', 'name', 'shared', 'created_by', 'card_count']


class FlashcardSerializer(WorkspaceSerializer):
    class Meta(WorkspaceSerializer.Meta):
        model = models.Flashcard
        fields = ['id', 'deck', 'question', 'answer', 'created_by']

    def validate(self, attrs):
        deck = attrs.get('deck', getattr(self.instance, 'deck', None))
        if deck.tenant_id != self.workspace().pk or deck.created_by_id != self.context['request'].user.pk:
            raise serializers.ValidationError({'deck': 'Only the deck owner can change its cards.'})
        if self.instance and deck.pk != self.instance.deck_id:
            raise serializers.ValidationError({'deck': 'Cards cannot be moved to another deck.'})
        for key in ('question', 'answer'):
            if len(attrs.get(key, '')) > 10000:
                raise serializers.ValidationError({key: 'Use up to 10000 characters.'})
        return attrs


def validate_fields(fields):
    if not isinstance(fields, list) or not 1 <= len(fields) <= 30:
        raise serializers.ValidationError('Add between 1 and 30 fields.')
    keys = set()
    clean = []
    for field in fields:
        if not isinstance(field, dict):
            raise serializers.ValidationError('Invalid field.')
        key, kind, label = field.get('key'), field.get('type'), field.get('label')
        if not isinstance(key, str) or not key.isidentifier() or len(key) > 50 or key in keys:
            raise serializers.ValidationError('Field keys must be unique names of up to 50 characters.')
        if kind not in ('text', 'textarea', 'email', 'choice', 'dropdown') or not isinstance(label, str) or not label.strip() or len(label) > 180:
            raise serializers.ValidationError('Choose a supported field type and a label.')
        options = field.get('options', [])
        if kind in ('choice', 'dropdown'):
            if not isinstance(options, list) or not 1 <= len(options) <= 30 or any(not isinstance(x, str) or not x.strip() or len(x) > 150 for x in options) or len(set(options)) != len(options):
                raise serializers.ValidationError('Choice fields need unique, nonempty options.')
        keys.add(key)
        clean.append({'key': key, 'type': kind, 'label': label.strip(), 'required': bool(field.get('required', False)), 'options': options if kind in ('choice', 'dropdown') else []})
    return clean


class FormSerializer(WorkspaceSerializer):
    fields = serializers.JSONField()
    class Meta(WorkspaceSerializer.Meta):
        model = models.Form
        fields = ['id', 'public_id', 'title', 'description', 'fields', 'published', 'version', 'created_by']
        read_only_fields = WorkspaceSerializer.Meta.read_only_fields + ['public_id', 'version']

    validate_fields = staticmethod(validate_fields)


class FeedbackWidgetSerializer(WorkspaceSerializer):
    class Meta(WorkspaceSerializer.Meta):
        model = models.FeedbackWidget
        fields = ['id', 'public_id', 'name', 'allowed_origins', 'label', 'enabled', 'created_by']
        read_only_fields = WorkspaceSerializer.Meta.read_only_fields + ['public_id']

    def validate_allowed_origins(self, origins):
        if not isinstance(origins, list) or not 1 <= len(origins) <= 20:
            raise serializers.ValidationError('Register between 1 and 20 website origins.')
        clean = []
        for origin in origins:
            if not isinstance(origin, str):
                raise serializers.ValidationError('Origins must be URLs.')
            safe_url(origin)
            parts = urlsplit(origin)
            if parts.path not in ('', '/') or parts.query or parts.fragment:
                raise serializers.ValidationError('Use an origin such as https://example.com, without a path.')
            authority = parts.netloc.lower()
            if parts.port == (443 if parts.scheme == 'https' else 80):
                authority = parts.hostname.lower()
            clean.append(f'{parts.scheme}://{authority}')
        return list(dict.fromkeys(clean))


class FeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Feedback
        fields = ['id', 'widget', 'message', 'email', 'page_url', 'status', 'task', 'submitted_at']
        read_only_fields = ['id', 'widget', 'message', 'email', 'page_url', 'task', 'submitted_at']


class FeedbackInput(serializers.Serializer):
    message = serializers.CharField(max_length=5000)
    email = serializers.EmailField(required=False, allow_blank=True)
    page_url = serializers.URLField(max_length=1000, required=False, allow_blank=True)
    website = serializers.CharField(required=False, allow_blank=True, max_length=200)


class WikiSerializer(WorkspaceSerializer):
    class Meta(WorkspaceSerializer.Meta):
        model = models.WikiPage
        fields = ['id', 'title', 'body', 'parent', 'created_by', 'updated_at']

    def validate(self, attrs):
        parent = attrs.get('parent', getattr(self.instance, 'parent', None))
        seen = {self.instance.pk} if self.instance else set()
        while parent:
            if parent.tenant_id != self.workspace().pk or parent.pk in seen:
                raise serializers.ValidationError({'parent': 'Choose a page in this workspace without a parent cycle.'})
            seen.add(parent.pk)
            parent = parent.parent
        if len(attrs.get('body', '')) > 100000:
            raise serializers.ValidationError({'body': 'Use up to 100000 characters.'})
        return attrs


class ApprovalSerializer(WorkspaceSerializer):
    class Meta(WorkspaceSerializer.Meta):
        model = models.ApprovalFile
        fields = ['id', 'client', 'title', 'file', 'version', 'client_user', 'status', 'approved_at', 'approved_by', 'comment', 'created_by']
        read_only_fields = WorkspaceSerializer.Meta.read_only_fields + ['version', 'status', 'approved_at', 'approved_by', 'comment']

    def validate(self, attrs):
        client = attrs.get('client', getattr(self.instance, 'client', None))
        user = attrs.get('client_user', getattr(self.instance, 'client_user', None))
        if client.tenant_id != self.workspace().pk or not active_memberships(user).filter(tenant=self.workspace()).exists():
            raise serializers.ValidationError('Choose a client and reviewer in this workspace.')
        uploaded = attrs.get('file')
        if uploaded and uploaded.size > 20 * 1024 * 1024:
            raise serializers.ValidationError({'file': 'Files must be at most 20 MB.'})
        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['file'] = f'/tools/approvals/{instance.pk}/download/'
        return data


class TimeLogSerializer(WorkspaceSerializer):
    class Meta(WorkspaceSerializer.Meta):
        model = models.TimeLog
        fields = ['id', 'task', 'work_date', 'hours', 'note', 'billable', 'created_by']

    def validate(self, attrs):
        task = attrs.get('task', getattr(self.instance, 'task', None))
        if task.project.tenant_id != self.workspace().pk or not can_view_project(self.context['request'].user, task.project):
            raise serializers.ValidationError({'task': 'Choose a task you can access.'})
        if not 0 < attrs.get('hours', getattr(self.instance, 'hours', 0)) <= 24:
            raise serializers.ValidationError({'hours': 'Hours must be greater than zero and at most 24.'})
        return attrs
