import json
from django.conf import settings
from channels.generic.websocket import WebsocketConsumer
from asgiref.sync import async_to_sync
from django.contrib.auth.models import AnonymousUser
from libs.msfws import Notify, Console
from homados.contrib.cache import MsfConsoleCache
from libs.pymetasploit.jsonrpc import MsfJsonRpc, MsfRpcError


logger = settings.LOGGER

msfjsonrpc = MsfJsonRpc(server=settings.MSFCONFIG['HOST'], port=settings.MSFCONFIG['JSONRPC']['PORT'], token=settings.MSFCONFIG['JSONRPC']['TOKEN'])


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
    def connect(self):
        super().connect()
        self.cache = MsfConsoleCache(self.scope['user'].username)
        self.console = Console(self.channel_name)

    def disconnect(self, code):
        self.console.close()
        return super().disconnect(code)
    
    def send_message(self, event):
        message = event['message']
        if not isinstance(message, str):
            message = json.dumps(message)
        self.send(message)
    
    def pack_msf_output(self, event):
        message = event['message']
        message = json.loads(message)
        logger.debug(message)
        data: str = message.get('data', '').replace('\n', '\r\n')
        prompt: str = message.get('prompt', '')
        data += prompt
        self.send_input_feedback(data)

    # TODO: 策略模式抽取
    def receive(self, text_data=None, bytes_data=None):
        message = json.loads(text_data)
        input_data = message.get("data")
        
        cache_input = self.cache.msfconsole_input_cache
        if input_data == '\r' or input_data == '\r\n':
            # 加入命令历史
            self.cache.msfconsole_history_add(cache_input)
            if cache_input.lower() == 'exit -f':
                cache_input = 'exit'
            # 发送命令
            self.console.send(cache_input + '\r\n')
            # 清空命令输入
            self.cache.msfconsole_input_cache_clear()
            self.send_input_feedback("\r\n")
        elif input_data == '\x7f': # backspace 键
            result = self.cache.msfconsole_input_cache_backspace()
            self.send_input_feedback(result)
        elif input_data == '\t': # tab 键
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
        elif input_data == "\x1b[A":  # 上键
            clear_cmd = self.cache.msfconsole_input_cache_clear_online()
            self.send_input_feedback(clear_cmd)
            last_cmd = self.cache.msfconsole_history_cache_last()
            if last_cmd:
                self.cache.msfconsole_input_cache_append(last_cmd)
                self.send_input_feedback(last_cmd)
        elif input_data == "\x1b[B": # 下键
            clear_cmd = self.cache.msfconsole_input_cache_clear_online()
            self.send_input_feedback(clear_cmd)
            next_cmd = self.cache.msfconsole_history_cache_next()
            if next_cmd:
                self.cache.msfconsole_input_cache_append(next_cmd)
                self.send_input_feedback(next_cmd)
        elif input_data == '\x03':  # ctrl+c
            msfjsonrpc.consoles.console(self.console.cid).sessionkill()
            self.cache.msfconsole_input_cache_clear()
            self.console.send('\r\n')
            self.send_input_feedback('\r\n')
        elif input_data == '\x1a':  # ctrl+z
            msfjsonrpc.consoles.console(self.console.cid).sessiondetach()
            self.cache.msfconsole_input_cache_clear()
            self.console.send('\r\n')
            self.send_input_feedback('\r\n')
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
        async_to_sync(self.channel_layer.group_add)(CustomerGroup.MsfNotify, self.channel_name)
        Notify(CustomerGroup.MsfNotify)
    
    def disconnect(self, code):
        async_to_sync(self.channel_layer.group_discard)(CustomerGroup.MsfNotify, self.channel_name)
        return super().disconnect(code)
    
    def send_message(self, event):
        message = event['message']
        self.send(message)
