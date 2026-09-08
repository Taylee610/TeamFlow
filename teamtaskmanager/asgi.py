"""
ASGI config for teamtaskmanager project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teamtaskmanager.settings')

django_asgi_app = get_asgi_application()

import projects.routing
import chat.routing
from chat.middleware import JWTAuthMiddlewareStack

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": JWTAuthMiddlewareStack(
        URLRouter(
            projects.routing.websocket_urlpatterns + chat.routing.websocket_urlpatterns
        )
    ),
})
