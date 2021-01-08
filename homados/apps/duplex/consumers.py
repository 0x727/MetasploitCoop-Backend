import base64
import json
import re

import chardet
from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
from django.conf import settings
from django.contrib.auth.models import AnonymousUser

from homados.contrib.cache import MsfConsoleCache
from libs.msfws import Console, Notify
from libs.pymetasploit.jsonrpc import MsfJsonRpc, MsfRpcError
from homados.contrib import mychannels

logger = settings.LOGGER

msfjsonrpc = settings.MSFJSONRPC


class CustomerGroup:
    __solts__ = ['Notify', 'MsfConsole']
    Notify = 'Notify'
    MsfConsole = 'MsfConsole'


class BaseCustomer(mychannels.AuthCustomer):
    def connect(self):
        super().connect()

    def send_message(self, event):
        message = event['message']
        if not isinstance(message, str):
            message = json.dumps(message)
        self.send(message)


# TODO: 重新启动一个新终端
class MsfConsoleCustomer(BaseCustomer):
    def connect(self):
        super().connect()
        self.cache = MsfConsoleCache(self.scope['user'].username)
        self.console = Console(self.channel_name)

    def disconnect(self, code):
        self.console.close()
    
    def pack_msf_output(self, event):
        message = event['message']
        message = json.loads(message)
        logger.debug(message)
        data: str = message.get('data', '')
        if data:
            data_bytes = base64.b64decode(data)
            result = chardet.detect(data_bytes)
            try:
                data = data_bytes.decode(result['encoding'] or 'utf-8')
            except UnicodeDecodeError as e:
                data = data_bytes.decode('utf-8')
        data = data.replace('\n', '\r\n')
        prompt: str = message.get('prompt', '')
        data += prompt
        # 有消息来的时候清空输入缓冲区
        self.cache.msfconsole_input_cache_clear()
        self.send_input_feedback(data)
    
    def key_enter_handler(self, cache_input):
        """处理回车键"""
        # 如果上一次是回车（连续回车）返回prompt
        if not cache_input:
            self.send_input_feedback(f'\r\n{self.console.prompt}')
            return
        self.cache.msfconsole_history_add(cache_input)
        if cache_input.strip().lower() == 'exit -f':
            cache_input = 'exit'
        elif re.match(r'sessions \d+?|sessions -i|pry|irb|edit|log', cache_input.strip().lower()):
            self.cache.msfconsole_input_cache_clear()
            self.send_input_feedback(f'\r\n交互模式已禁用，执行命令请右击会话\r\n{self.console.prompt}')
            return
        # 发送命令
        self.console.send(cache_input + '\r\n')
        # 清空命令输入
        self.cache.msfconsole_input_cache_clear()
        self.send_input_feedback("\r\n")
    
    def key_backspace_handler(self, cache_input):
        """处理退格键"""
        result = self.cache.msfconsole_input_cache_backspace()
        self.send_input_feedback(result)
    
    def key_tab_handler(self, cache_input):
        """处理tab键"""
        tabs = msfjsonrpc.consoles.console(self.console.cid).tabs(cache_input)
        if not tabs:
            return
        elif len(tabs) == 1:
            extra_str = tabs[0][len(cache_input):]
            self.send_input_feedback(extra_str)
            self.cache.msfconsole_input_cache_append(extra_str)
        else:
            tmp = self.handle_tabs(cache_input, tabs)
            # 如果返回的结果与之前的输入不相等则有补全，否则列出所有的补全项
            if tmp != cache_input:
                extra_str = tmp[len(cache_input):]
                self.send_input_feedback(extra_str)
                self.cache.msfconsole_input_cache_append(extra_str)
            else:
                extra_str = "\r\n"
                for one in tabs:
                    extra_str += one + "\r\n"
                prompt = self.console.prompt
                extra_str = extra_str + prompt + cache_input
                self.send_input_feedback(extra_str)
    
    def key_up_handler(self, cache_input):
        """处理上键"""
        clear_cmd = self.cache.msfconsole_input_cache_clear_online()
        self.send_input_feedback(clear_cmd)
        last_cmd = self.cache.msfconsole_history_cache_last()
        if last_cmd:
            self.cache.msfconsole_input_cache_append(last_cmd)
            self.send_input_feedback(last_cmd)

    def key_down_handler(self, cache_input):
        """处理下键"""
        clear_cmd = self.cache.msfconsole_input_cache_clear_online()
        self.send_input_feedback(clear_cmd)
        next_cmd = self.cache.msfconsole_history_cache_next()
        if next_cmd:
            self.cache.msfconsole_input_cache_append(next_cmd)
            self.send_input_feedback(next_cmd)
    
    def key_ctrl_c_handler(self, cache_input):
        """处理ctrl+c"""
        msfjsonrpc.consoles.console(self.console.cid).sessionkill()
        self.cache.msfconsole_input_cache_clear()
        self.console.send('\r\n')
        self.send_input_feedback('\r\n')
    
    def key_ctrl_z_handler(self, cache_input):
        """处理ctrl+z"""
        msfjsonrpc.consoles.console(self.console.cid).sessiondetach()
        self.cache.msfconsole_input_cache_clear()
        self.console.send('\r\n')
        self.send_input_feedback('\r\n')

    @property
    def key_event_map(self):
        if not hasattr(self, '_key_event_map'):
            self._key_event_map = {
                '\r': self.key_enter_handler,
                '\r\n': self.key_enter_handler,
                '\x7f': self.key_backspace_handler,
                '\t': self.key_tab_handler,
                '\x1b[A': self.key_up_handler,
                '\x1b[B': self.key_down_handler,
                '\x03': self.key_ctrl_c_handler,
                '\x1a': self.key_ctrl_z_handler,
            }
        return self._key_event_map

    def receive(self, text_data=None, bytes_data=None):
        message = json.loads(text_data)
        input_data = message.get("data")
        
        cache_input = self.cache.msfconsole_input_cache
        key_handler = self.key_event_map.get(input_data)
        if key_handler:
            key_handler(cache_input)
        else:
            self.cache.msfconsole_input_cache_append(input_data)
            self.send_input_feedback(input_data)

    def handle_tabs(self, cur_input, tabs):
        """根据当前的输入从诸多的自动补全中达到一个最长的补全结果

        例子：handle_tabs('he', ['help/xxx', 'help/fff']) -> 'help/'
        """
        newlength = len(cur_input) + 1
        return_str = cur_input
        while True:
            if newlength >= len(tabs[0]):
                return tabs[0][0:newlength]
            tmp_str = tabs[0][0:newlength]
            for one_tab in tabs:
                if tmp_str not in one_tab:
                    return return_str
            return_str = tmp_str
            newlength = newlength + 1

    def send_input_feedback(self, data=''):
        """给前端回送消息"""
        message = {}
        message['status'] = 0
        message['data'] = data
        async_to_sync(self.channel_layer.send)(
            self.channel_name,
            {
                'type': 'send_message',
                'message': message
            }
        )


class MsfNotifyCustomer(BaseCustomer):
    def connect(self):
        super().connect()
        async_to_sync(self.channel_layer.group_add)(CustomerGroup.Notify, self.channel_name)
        Notify(CustomerGroup.Notify)
    
    def disconnect(self, code):
        async_to_sync(self.channel_layer.group_discard)(CustomerGroup.Notify, self.channel_name)
