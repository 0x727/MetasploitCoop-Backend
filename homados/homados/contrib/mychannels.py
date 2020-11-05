from channels.generic.websocket import WebsocketConsumer
from django.contrib.auth.models import AnonymousUser
from django.conf import settings


logger = settings.LOGGER


class AuthCustomer(WebsocketConsumer):
    def connect(self):
        self.accept()
        if isinstance(self.scope['user'], AnonymousUser):
            return self.disconnect(403)
        client_addr = ':'.join([str(i) for i in self.scope["client"]])
        logger.info(f'[{self.__class__.__name__}] {client_addr} websocket 建立连接')
