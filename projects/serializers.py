from rest_framework import serializers
from .models import Project, Task
from accounts.models import User
from accounts.serializers import UserSerializer
from accounts.permissions import can_manage_project, can_view_project
from erp_foundation.access import workspace_membership, active_memberships

class ProjectSerializer(serializers.ModelSerializer):
    owner = UserSerializer(read_only=True)
    members = UserSerializer(many=True, read_only=True)
    can_manage = serializers.SerializerMethodField()

    def get_can_manage(self, obj):
        request = self.context.get('request')
        return bool(request and can_manage_project(request.user, obj))

    class Meta:
        model = Project
        fields = ['id','name','description','owner','members','created_at','can_manage']


class AddMemberSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        try:
            return User.objects.get(email__iexact=value)
        except User.DoesNotExist:
            raise serializers.ValidationError('No user with that email exists yet -- they need to sign up first.')

class TaskSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.attachment:
            data['attachment'] = f'/files/tasks/{instance.pk}/'
        return data

    project = serializers.PrimaryKeyRelatedField(queryset=Project.objects.all())
    assigned_to = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), allow_null=True,required=False)
    attachment = serializers.FileField(required=False,allow_null=True)

    class Meta:
             model = Task
             fields = ['id','project','title','description','status','priority','due_date','assigned_to','updated_at','attachment','parent','linked_tasks','labels','story_points']

    def validate(self, attrs):
        project = attrs.get('project') or getattr(self.instance, 'project', None)
        request = self.context.get('request')
        if request and (project.tenant_id != workspace_membership(request).tenant_id or not can_view_project(request.user, project)):
            raise serializers.ValidationError({'project': 'Project is not available in this workspace.'})
        # Moving a task also affects its children, links, attachments and audience.
        # Keep the project fixed until a dedicated, authorized transfer exists.
        if self.instance and project.pk != self.instance.project_id:
            raise serializers.ValidationError({'project': 'Tasks cannot be moved between projects.'})
        if 'assigned_to' in attrs and attrs['assigned_to'] is not None:
            assignee = attrs['assigned_to']
            if not active_memberships(assignee).filter(tenant_id=project.tenant_id).exists() or not (
                project.owner_id == assignee.pk or project.members.filter(pk=assignee.pk).exists()
            ):
                raise serializers.ValidationError({'assigned_to': 'Choose an active owner or member of this project.'})
        parent = attrs.get('parent')
        linked = attrs.get('linked_tasks', [])
        if self.instance and parent:
            seen = {self.instance.pk}
            ancestor = parent
            while ancestor:
                if ancestor.pk in seen:
                    raise serializers.ValidationError({'parent': 'Task hierarchy cannot contain a cycle.'})
                seen.add(ancestor.pk)
                ancestor = ancestor.parent
        if self.instance and any(task.pk == self.instance.pk for task in linked):
            raise serializers.ValidationError({'linked_tasks': 'A task cannot link to itself.'})
        if parent and project and parent.project_id != project.id:
            raise serializers.ValidationError({'parent': 'A child task must belong to the same project.'})
        if project and any(task.project_id != project.id for task in linked):
            raise serializers.ValidationError({'linked_tasks': 'Linked tasks must belong to the same project.'})
        return attrs
