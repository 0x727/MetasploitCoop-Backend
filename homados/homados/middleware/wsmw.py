# websocket middleware

from channels.middleware import BaseMiddleware
from channels.auth import UserLazyObject
from django.conf import settings
from importlib import import_module
from channels.auth import get_user
from urllib.parse import parse_qs


# TODO: 跟踪 github.com/django/channels/issues/1399 至文档更新
class QueryXTokenAuthMiddleware(BaseMiddleware):
    """时间节点 202009151617
    一段来自 https://github.com/django/channels/issues/1399 的魔法（django3+channel后出现的问题）
    
    直接按照 https://channels.readthedocs.io/en/latest/topics/authentication.html#custom-authentication 写
    验证中间件会获取不到user"""
    def populate_scope(self, scope):
        self.SessionStore = import_module(settings.SESSION_ENGINE).SessionStore
        params = parse_qs(scope.get('query_string', b'').decode())
        session_key = params.get('token')
        session_key = session_key[0] if session_key else None
        session = self.SessionStore(session_key)
        scope['session'] = session
        if "user" not in scope:
            scope["user"] = UserLazyObject()

    async def resolve_scope(self, scope):
        scope["user"]._wrapped = await get_user(scope)
