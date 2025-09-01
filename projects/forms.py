from django import forms
from .models import Task,Project

class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ('title', 'description', 'status', 'due_date', 'assigned_to', 'attachment')
        widgets = {'due_date':forms.DateInput(attrs={'type':'date'}),}

class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ('name', 'description')