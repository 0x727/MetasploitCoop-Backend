"""
ASGI config for homados project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.1/howto/deployment/asgi/
"""

import os

from channels.routing import ProtocolTypeRouter
from django.core.asgi import get_asgi_application
from homados.middleware.wsmw import QueryXTokenAuthMiddleware
from channels.routing import ProtocolTypeRouter, URLRouter
import apps.duplex.routing
import apps.synergy.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'homados.settings.dev_micro')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    # Just HTTP for now. (We can add other protocols later.)
    'websocket': QueryXTokenAuthMiddleware(
        URLRouter(
            # msf 执行结果推送
            apps.duplex.routing.websocket_urlpatterns +
            # 聊天室
            apps.synergy.routing.websocket_urlpatterns
        )
    ),
})
