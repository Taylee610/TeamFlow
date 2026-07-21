"""
URL configuration for teamtaskmanager project.

Django is a pure JSON API here -- the React app in /src is the UI and
talks to these endpoints directly (JWT auth).
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from core.views import api_root

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', api_root, name='api-root'),
    path('api/', include('projects.api_urls')),
    path('api/chat/', include('chat.api_urls')),
    path('api/auth/', include('accounts.api_urls')),
    path('api/ai/', include('ai_assistant.urls')),
    path('api/v1/erp/', include('accounting.api_urls')),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
