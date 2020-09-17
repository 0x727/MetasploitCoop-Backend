import json
import threading
import channels
import websocket
from django.conf import settings
from asgiref.sync import async_to_sync

from .utils import Singleton
import time

logger = settings.LOGGER


# TODO: 抽出基类
# TODO: ws重连机制


class Notify(metaclass=Singleton):
    """msf 提醒，一个系统中只需要一个实例，无需close"""
    def __init__(self, group_name: str):
        self.group_name = group_name
        token = settings.MSFCONFIG['JSONRPC']['TOKEN']
        host = settings.MSFCONFIG['HOST']
        port = settings.MSFCONFIG['JSONRPC']['PORT']
        self.ws_addr = f'ws://{host}:{port}/api/v1/websocket/notify'
        self.channel_layer = channels.layers.get_channel_layer()
        ws = websocket.WebSocketApp(
            self.ws_addr,
            header={'Authorization': f'Bearer {token}'},
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        setattr(ws, 'channel_layer', self.channel_layer)
        setattr(ws, 'group_name', self.group_name)
        wst = threading.Thread(target=ws.run_forever)
        wst.daemon = True
        wst.start()

    @staticmethod
    def on_open(ws):
        logger.info(f'与 msf notify 建立连接')

    @staticmethod
    def on_message(ws, message):
        async_to_sync(ws.channel_layer.group_send)(
            ws.group_name,
            {
                'type': 'send_message',
                'message': message
            }
        )

    @staticmethod
    def on_error(ws, error):
        logger.error(error)

    @staticmethod
    def on_close(ws):
        logger.error(f'与 msf notify 的连接异常关闭')


class Console:
    def __init__(self, channel_name: str):
        self.channel_name = channel_name
        self.token = settings.MSFCONFIG['JSONRPC']['TOKEN']
        host = settings.MSFCONFIG['HOST']
        port = settings.MSFCONFIG['JSONRPC']['PORT']
        self.ws_addr = f'ws://{host}:{port}/api/v1/websocket/console'
        self.channel_layer = channels.layers.get_channel_layer()
        # lambda 函数主要是为了把 self 传入 callback function
        self.ws = websocket.WebSocketApp(
            self.ws_addr,
            header = {'Authorization': f'Bearer {self.token}'},
            on_open = lambda ws: self.on_open(ws),
            on_message = lambda ws, msg: self.on_message(ws, msg),
            on_error = lambda ws, msg: self.on_error(ws, msg),
            on_close = lambda ws: self.on_close(ws)
        )
        wst = threading.Thread(target=self.ws.run_forever)
        wst.daemon = True
        wst.start()

    def __getattr__(self, name):
        if hasattr(self.ws, name):
            return getattr(self.ws, name)
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

    @property
    def cid(self):
        while True:
            if hasattr(self, 'console_id'):
                return self.console_id
            self.ws.send('\r\n')
            time.sleep(1)

    def on_open(self, ws):
        logger.info(f'与 msf console 建立连接')

    def on_message(self, ws, message):
        data = json.loads(message)
        self.console_id = data['cid']
        self.prompt = data['prompt']
        async_to_sync(self.channel_layer.send)(
            self.channel_name,
            {
                'type': 'pack_msf_output',
                'message': message
            }
        )

    def on_error(self, ws, error):
        logger.error(error)

    def on_close(self, ws):
        logger.error(f'与 msf console 的连接异常关闭')
