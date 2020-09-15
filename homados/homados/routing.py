from channels.auth import AuthMiddlewareStack
from homados.middleware.wsmw import QueryXTokenAuthMiddleware
from channels.routing import ProtocolTypeRouter, URLRouter
import apps.duplex.routing

application = ProtocolTypeRouter({
    # (http->django views is added by default)
    'websocket': QueryXTokenAuthMiddleware(
        URLRouter(
            apps.duplex.routing.websocket_urlpatterns
        )
    ),
})