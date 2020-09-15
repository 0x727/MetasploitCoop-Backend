from django.conf import settings
from channels.generic.websocket import WebsocketConsumer
from asgiref.sync import async_to_sync
from django.contrib.auth.models import AnonymousUser
from libs.msfws import Notify


logger = settings.LOGGER


class CustomerGroup:
    __solts__ = ['MsfNotify', 'MsfConsole']
    MsfNotify = 'MsfNotify'
    MsfCOnsole = 'MsfConsole'


class BaseCustomer(WebsocketConsumer):
    def connect(self):
        self.accept()
        if isinstance(self.scope['user'], AnonymousUser):
            return self.disconnect()
        client_addr = ':'.join([str(i) for i in self.scope["client"]])
        logger.info(f'[{self.__class__.__name__}] {client_addr} websocket 建立连接')


class MsfConsoleCustomer(BaseCustomer):
    def connect(self):
        super().connect()
        # TODO: 创建msf console(用户session储存)

    def disconnect(self, code):
        # TODO: 删除msf console(用户session储存)
        return super().disconnect(code)

    def receive(self, text_data=None, bytes_data=None):
        return super().receive(text_data=self.scope['user'].username)


class MsfNotifyCustomer(BaseCustomer):
    def connect(self):
        super().connect()
        async_to_sync(self.channel_layer.group_add)(CustomerGroup.MsfNotify, self.channel_name)
        Notify(CustomerGroup.MsfNotify)
    
    def disconnect(self, code):
        async_to_sync(self.channel_layer.group_discard)(CustomerGroup.MsfNotify, self.channel_name)
        return super().disconnect(code)
    
    def send_message(self, event):
        message = event['message']
        self.send(message)
