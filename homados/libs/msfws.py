import json
import threading
import channels
import websocket
from django.conf import settings
from asgiref.sync import async_to_sync

from .utils import Singleton
import time

logger = settings.LOGGER


class BaseWS:
    def __init__(self, receiver_name: str):
        self.receiver_name = receiver_name
        # lambda 函数主要是为了把 self 传入 callback function
        self.ws = websocket.WebSocketApp(
            self.get_ws_addr(),
            header = {'Authorization': f'Bearer {self.jsonrpc_token}'},
            on_open = lambda ws: self.on_open(ws),
            on_message = lambda ws, msg: self.on_message(ws, msg),
            on_error = lambda ws, msg: self.on_error(ws, msg),
            on_close = lambda ws: self.on_close(ws),
            on_ping = lambda ws, data: self.on_ping(ws, data),
            on_pong = lambda ws, data: self.on_pong(ws, data),
        )
        self.connect_to_ws()
    
    @property
    def jsonrpc_token(self):
        return settings.MSFCONFIG['JSONRPC']['TOKEN']
    
    @property
    def jsonrpc_host(self):
        return settings.MSFCONFIG['HOST']
    
    @property
    def jsonrpc_port(self):
        return settings.MSFCONFIG['JSONRPC']['PORT']

    def get_ws_addr(self):
        raise NotImplementedError

    def connect_to_ws(self):
        def _to_connect():
            self.ws.run_forever(ping_interval=60, ping_timeout=5)
        wst = threading.Thread(target=_to_connect)
        wst.daemon = True
        wst.start()

    def on_open(self, ws):
        logger.info(f'<{self.__class__.__name__}> 与 msf 建立连接')
    
    def on_close(self, ws):
        logger.warning(f'<{self.__class__.__name__}> 与 msf 断开连接')
    
    def on_error(self, ws, error):
        logger.error(f'<{self.__class__.__name__}> 与 msf 的连接出现错误, {error}')
    
    def on_ping(self, ws, data):
        logger.debug(f'<{self.__class__.__name__}> 发送 ping, {data}')
    
    def on_pong(self, ws, data):
        logger.debug(f'<{self.__class__.__name__}> 接收 pong, {data}')
    
    def on_message(self, ws, message):
        raise NotImplementedError


class Notify(BaseWS, metaclass=Singleton):
    """msf 提醒，一个系统中只需要一个实例，无需close"""
    def get_ws_addr(self):
        return f'ws://{self.jsonrpc_host}:{self.jsonrpc_port}/api/v1/websocket/notify'

    def on_message(self, ws, message):
        self.send_ws_msg(message)

    def send_ws_msg(self, message):
        self.channel_layer = channels.layers.get_channel_layer()
        async_to_sync(self.channel_layer.group_send)(
            self.receiver_name,
            {
                'type': 'send_message',
                'message': message
            }
        )

    def connect_to_ws(self):
        """支持自动重连"""
        def reconnect():
            while self.ws.run_forever(ping_interval=60, ping_timeout=5):
                time.sleep(5)
                logger.info(f'<{self.__class__.__name__}> 正在尝试重连')
        wst = threading.Thread(target=reconnect)
        wst.daemon = True
        wst.start()


class Console(BaseWS):
    def __getattr__(self, name):
        if hasattr(self.ws, name):
            return getattr(self.ws, name)
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

    def get_ws_addr(self):
        return f'ws://{self.jsonrpc_host}:{self.jsonrpc_port}/api/v1/websocket/console'

    def on_message(self, ws, message):
        self.channel_layer = channels.layers.get_channel_layer()
        data = json.loads(message)
        self.cid = data['cid']
        self.prompt = data['prompt']
        async_to_sync(self.channel_layer.send)(
            self.receiver_name,
            {
                'type': 'pack_msf_output',
                'message': message
            }
        )
