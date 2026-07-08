from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import TokenError


@database_sync_to_async
def _get_user_from_token(token):
    from accounts.models import User
    try:
        access = AccessToken(token)
        return User.objects.get(pk=access['user_id'])
    except (TokenError, User.DoesNotExist, KeyError):
        return AnonymousUser()


class JWTAuthMiddleware:
    """Channels middleware that authenticates a WebSocket connection using
    the same JWT access token the React app already sends on the
    Authorization header for REST calls.

    Browsers can't set custom headers on a WebSocket handshake, so the
    token is passed as a query string param instead:

        wss://.../ws/chat/conversations/5/?token=<access_token>
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        query_string = scope.get('query_string', b'').decode()
        token = parse_qs(query_string).get('token', [None])[0]

        scope['user'] = await _get_user_from_token(token) if token else AnonymousUser()
        return await self.app(scope, receive, send)


def JWTAuthMiddlewareStack(app):
    return JWTAuthMiddleware(app)