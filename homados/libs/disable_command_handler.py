import re
from django.conf import settings
from libs.pymetasploit.jsonrpc import MsfJsonRpc


logger = settings.LOGGER


msfjsonrpc = MsfJsonRpc(
    server=settings.MSFCONFIG['HOST'],
    port=settings.MSFCONFIG['JSONRPC']['PORT'],
    token=settings.MSFCONFIG['JSONRPC']['TOKEN'],
)

class CommandTips:
    __solts__ = ['can_exec', 'tips']

    def __init__(self, can_exec=False, tips=''):
        self.can_exec = can_exec
        self.tips = tips


def handle_command_shell(command: str, instance=None, *args, **kwargs):
    """处理shell命令
    
    Args:
        command: 输入的命令
        instance: 可以任意传入的对象
        kwargs:
            sid: 会话id
    Returns:
        返回是否可执行以及提示
    """
    if 'sid' not in kwargs:
        raise KeyError('缺少 sid 参数')
    cmd = command.strip()
    if not (cmd.startswith('shell ') and len(cmd) > len('shell ')):
        return CommandTips(False, '不支持进入交互式shell，请使用shell whoami来执行')
    cmd = cmd[len('shell '):]
    cmd_args = cmd.split()
    cmd = cmd_args.pop(0)
    args = cmd_args
    msfjsonrpc.sessions.session(int(kwargs['sid'])).cmd_exec(cmd, args, timeout=120)
    return CommandTips(True, f'> {command}')


def handle_general_disable(msg: str):
    def handle(command: str, instance=None, *args, **kwargs):
        if 'sid' not in kwargs:
            raise KeyError('缺少 sid 参数')
        return CommandTips(False, msg)
    return handle
    

disable_command_handler = {
    re.compile(r'^shell$|^shell .*'): handle_command_shell,
    re.compile(r'^run$|^run .*'): handle_general_disable('不支持run指令，请使用post模块代替'),
    re.compile(r'^edit$|^edit .*'): handle_general_disable('不支持edit指令，请使用图形界面编辑'),
    re.compile(r'^screenshare$|^screenshare .*'): handle_general_disable('不支持screenshare指令'),
    re.compile(r'^pry$|^pry .*'): handle_general_disable('不支持pry指令'),
}
