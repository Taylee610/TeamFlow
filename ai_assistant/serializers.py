from rest_framework import serializers

from projects.models import Project


class TaskAssistRequestSerializer(serializers.Serializer):
    prompt = serializers.CharField(max_length=2000)
    project = serializers.PrimaryKeyRelatedField(queryset=Project.objects.all(), required=False, allow_null=True)


class TaskAssistResponseSerializer(serializers.Serializer):
    description = serializers.CharField()
    subtasks = serializers.ListField(child=serializers.CharField())
    priority = serializers.ChoiceField(choices=['low', 'medium', 'high'])
    due_date = serializers.CharField(allow_null=True)
