# websocket middleware

from channels.middleware import BaseMiddleware
from channels.auth import UserLazyObject
from django.conf import settings
from importlib import import_module
from channels.auth import get_user
from urllib.parse import parse_qs


class QueryXTokenAuthMiddleware:
    def __init__(self, app):
        # Store the ASGI application we were passed
        self.app = app

    async def __call__(self, scope, receive, send):
        # Look up user from query string (you should also do things like
        # checking if it is a valid user ID, or if scope["user"] is already
        # populated).
        self.SessionStore = import_module(settings.SESSION_ENGINE).SessionStore
        params = parse_qs(scope.get('query_string', b'').decode())
        session_key = params.get('token')
        session_key = session_key[0] if session_key else None
        session = self.SessionStore(session_key)
        scope['session'] = session
        scope['user'] = await get_user(scope)

        return await self.app(scope, receive, send)
