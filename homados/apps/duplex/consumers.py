import json
from django.conf import settings
from channels.generic.websocket import WebsocketConsumer
from asgiref.sync import async_to_sync
from django.contrib.auth.models import AnonymousUser
from libs.msfws import Notify, Console
from homados.contrib.cache import DistinctCacheProxy


logger = settings.LOGGER


class CustomerGroup:
    __solts__ = ['MsfNotify', 'MsfConsole']
    MsfNotify = 'MsfNotify'
    MsfCOnsole = 'MsfConsole'


class BaseCustomer(WebsocketConsumer):
    def connect(self):
        self.accept()
        if isinstance(self.scope['user'], AnonymousUser):
            return self.disconnect(403)
        client_addr = ':'.join([str(i) for i in self.scope["client"]])
        logger.info(f'[{self.__class__.__name__}] {client_addr} websocket 建立连接')


# TODO: 重新启动一个新终端
class MsfConsoleCustomer(BaseCustomer):
    CACHE_MSFCONSOLE_INPUT_CACHE = 'msfconsole:input:cache'
    CACHE_MSFCONSOLE_HISTORY_CACHE = 'msfconsole:history:cache'

    def connect(self):
        super().connect()
        self.cache = DistinctCacheProxy(self.scope['user'].username)
        self.console = Console(self.channel_name)

    def disconnect(self, code):
        self.console.close()
        return super().disconnect(code)
    
    def send_message(self, event):
        message = event['message']
        self.send(message)

    def receive(self, text_data=None, bytes_data=None):
        message = json.loads(text_data)
        input_data = message.get("data")
        
        cache_input = self.cache.get(self.CACHE_MSFCONSOLE_INPUT_CACHE) or ''
        if input_data == '\r' or input_data == '\r\n':
            # 加入命令历史
            self.cache.msfconsole_history_add(self.CACHE_MSFCONSOLE_HISTORY_CACHE, cache_input)
            if cache_input.lower() == 'exit -f':
                cache_input = 'exit'
            # 发送命令
            self.console.send(cache_input + '\r\n')
            # 清空命令输入
            self.cache.delete(self.CACHE_MSFCONSOLE_INPUT_CACHE)
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
