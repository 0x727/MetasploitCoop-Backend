import threading
import channels
import websocket
from django.conf import settings
from asgiref.sync import async_to_sync

from .utils import Singleton

logger = settings.LOGGER


class Notify(metaclass=Singleton):
    def __init__(self, group_name):
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
        logger.info(f'与 msf 建立连接')

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
        logger.error(f'与 msf 的连接异常关闭')
