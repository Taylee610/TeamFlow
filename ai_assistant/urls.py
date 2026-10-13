from django.urls import path

from .views import TaskAssistView, ProjectSummaryView, SavePlanView

urlpatterns = [
    path('save-plan/', SavePlanView.as_view(), name='ai-save-plan'),
    path('task-assist/', TaskAssistView.as_view(), name='ai-task-assist'),
    path('projects/<int:project_id>/summary/', ProjectSummaryView.as_view(), name='ai-project-summary'),
]
