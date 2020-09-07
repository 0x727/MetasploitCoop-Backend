"""session中间件"""
from django.contrib.sessions.backends.base import UpdateError
from django.core.exceptions import SuspiciousOperation
from django.contrib.sessions.middleware import SessionMiddleware
from django.conf import settings


class SessionCustomHeaderMiddleware(SessionMiddleware):
    """从自定义请求头取session并取消Set-Cookie头"""
    def process_request(self, request):
        session_key = request.headers.get(settings.SESSION_CUSTOM_HEADER)
        request.session = self.SessionStore(session_key)
    
    def process_response(self, request, response):
        if response.status_code != 500:
            try:
                request.session.save()
            except UpdateError:
                raise SuspiciousOperation(
                    "The request's session was deleted before the "
                    "request completed. The user may have logged "
                    "out in a concurrent request, for example."
                )
        return response
