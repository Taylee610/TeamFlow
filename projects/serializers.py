from rest_framework import serializers
from .models import Project, Task
from accounts.models import User
from accounts.serializers import UserSerializer

class ProjectSerializer(serializers.ModelSerializer):
    owner = UserSerializer(read_only=True)
    members = UserSerializer(many=True, read_only=True)

    class Meta:
        model = Project
        fields = ['id','name','description','owner','members','created_at']


class AddMemberSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        try:
            return User.objects.get(email__iexact=value)
        except User.DoesNotExist:
            raise serializers.ValidationError('No user with that email exists yet -- they need to sign up first.')

class TaskSerializer(serializers.ModelSerializer):
    project = serializers.PrimaryKeyRelatedField(queryset=Project.objects.all())
    assigned_to = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), allow_null=True,required=False)
    attachment = serializers.FileField(required=False,allow_null=True)

    class Meta:
             model = Task
             fields = ['id','project','title','description','status','priority','due_date','assigned_to','updated_at','attachment','parent','linked_tasks','labels','story_points']

    def validate(self, attrs):
        project = attrs.get('project') or getattr(self.instance, 'project', None)
        parent = attrs.get('parent')
        linked = attrs.get('linked_tasks', [])
        if parent and project and parent.project_id != project.id:
            raise serializers.ValidationError({'parent': 'A child task must belong to the same project.'})
        if project and any(task.project_id != project.id for task in linked):
            raise serializers.ValidationError({'linked_tasks': 'Linked tasks must belong to the same project.'})
        return attrs
