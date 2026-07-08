from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import ConversationViewSet, CannedResponseViewSet

router = DefaultRouter()
router.register('conversations', ConversationViewSet, basename='conversation')
router.register('canned-responses', CannedResponseViewSet, basename='canned-response')

urlpatterns = [
    path('', include(router.urls)),
]