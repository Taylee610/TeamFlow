from django.urls import path
from .views import(
    ProjectListView, ProjectDetailView, ProjectCreateView,
    ProjectDeleteView, TaskCreateView, TaskUpdateView
)

urlpatterns = [
    path("ProjectListView.as_view(), name='project-list')"),
    path('projects/new/', ProjectCreateView.as_view(), name='project-create'),
    path('projects/<int:pk>/', ProjectDetailView.as_view(), name='project-detail'),
    path('projects/<int:pk>/delete/', ProjectDeleteView.as_view(), name='project-delete'),


    path('projects/<int:project_pk>/tasks/new/', TaskCreateView.as_view(), name='task-create'),
    path('tasks/<int:pk>/edit/', TaskUpdateView.as_view(),name='task-edit'),
    path('tasks/<int:pk>/delete/', TaskDeleteView.as_view(), name='task-delete'),
]