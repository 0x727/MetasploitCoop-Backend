"""依托 https://github.com/phra/PEzor 项目的能力"""

import re
import subprocess
import uuid
import base64
from libs.options import Option
from libs.types import PayloadType

NAME = 'pezor'
DESC = '使用clang编译，支持导出 exe, dll, reflective-dll, service-exe, service-dll, dotnet, dotnet-createsection, dotnet-pinvoke'
TYPE = PayloadType.SHELLCODE_PACKER
OPTIONS = [
    Option(name='shellcode', name_tag='Shellcode文件', type='file', required=True, desc='所使用的msf payload shellcode'),
    Option(name='arch', name_tag='位数', type='enum', required=False, desc='系统位数', default='32', enums=['32', '64']),
    Option(name='debug', name_tag='debug版本', type='bool', desc='生成debug版本', required=False, default=False),
    Option(name='text', name_tag='text节', type='bool', desc='把shellcdoe放置到text节而不是data节', required=False, default=False),
    Option(name='self', name_tag='同线程', type='bool', desc='在相同的线程里面运行shellcode', required=False, default=False),
    Option(name='sleep', name_tag='休眠时间', type='integer', desc='在解压shellcode前休眠多少秒', required=False),
    Option(name='format', name_tag='生成格式', type='enum', desc='输出特定格式', required=False, default='exe', enums=['exe', 'dll', 'reflective-dll', 'service-exe', 'service-dll', 'dotnet', 'dotnet-createsection','dotnet-pinvoke']),
]
REFERENCES = ['https://github.com/phra/PEzor']
AUTHOR = 'Akkuman <akkumans@qq.com>'


def run(options=None, info=None):
    """payload生成
    Args:
        options: 上面的OPTIONS中的数据
        info: 外部传入的额外信息
    Returns:
        包含文件内容的文件字节流
    """
    from django.conf import settings
    from rest_framework import exceptions
    try:
        res = b''

        # 从msf生成shellcode
        bin_data = base64.b64decode(options.get('shellcode'))
        
        # 保存shellcode到文件
        uid = str(uuid.uuid4())
        src_filepath = settings.TMP_DIR.joinpath(f'{uid}.exe')
        with open(str(src_filepath), 'wb') as f:
            f.write(bin_data)
        cmds = _build_cmd(options, str(src_filepath))

        # 执行命令生成exe
        output = subprocess.check_output(cmds, timeout=120, stderr=subprocess.STDOUT).decode()
        search_res = re.search(r'\[\!\] Done\! Check (\S+): ', output)
        if not search_res:
            raise exceptions.APIException(detail=f'生成失败: {output}')
        out_filename = search_res.group(1)
        out_filepath = src_filepath.parent.joinpath(out_filename)
        with open(str(out_filepath), 'rb') as f:
            res = f.read()
        return res
    except subprocess.CalledProcessError as e:
        raise exceptions.APIException(detail=e.output.decode())
    except subprocess.TimeoutExpired as e:
        raise exceptions.APIException(detail='生成payload超时')


def _build_cmd(options, src):
    cmds = ['PEzor']
    if options.get('arch'):
        cmds.append(f"-{options.get('arch')}")
    if options.get('debug'):
        cmds.append(f"-debug")
    if options.get('text'):
        cmds.append(f"-text")
    if options.get('self'):
        cmds.append(f"-self")
    if options.get('sleep'):
        cmds.append(f"-sleep={options.get('sleep')}")
    if options.get('format'):
        cmds.append(f"-format={options.get('format')}")
    cmds.append(src)
    return cmds
