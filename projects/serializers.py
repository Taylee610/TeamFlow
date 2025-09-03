from rest_framework import serializers
from .models import Project, Task
from accounts.models import User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id','email','first_name','last_name']

class ProjectSerializer(serializers.ModelSerializer):
    owner = UserSerializer(read_only=True)

    class Meta:
        model = Project
        fields = ['id','name','description','owner','created_at']

class TaskSerializer(serializers.ModelSerializer):
    project = serializers.PrimaryKeyRelatedField(queryset=Project.objects.all())
    assigned_to = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), allow_null=True,required=False)
    attachment = serializers.FileField(required=False,allow_null=True)

    class Meta:
             model = Task
             fields = ['id','project','title','description','status','due_date','assigned_to','updated_at','attachment']
