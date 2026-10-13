from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import ProjectViewSet, TaskViewSet
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from accounts.recovery import LoginView, RefreshView

router = DefaultRouter()
router.register('projects', ProjectViewSet, basename='project')
router.register('tasks', TaskViewSet, basename='task')

urlpatterns = [
    path('auth/token/', LoginView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', RefreshView.as_view(), name='token_refresh'),
    path('', include(router.urls)),
]
