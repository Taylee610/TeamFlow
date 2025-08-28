from django.contrib import admin
from .models import Project, Task

class TaskInline(admin.TabularInline):
    model = Task
    extra = 0

class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'created_at')
    inlines = [TaskInline]

class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'project', 'status', 'assigned_to','due_date')
    list_filter = ('status', 'due_date')
    search_fields = ('title', 'description')