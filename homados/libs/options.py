"""为payload插件提供options"""
import base64
from django.conf import settings

logger = settings.LOGGER

option_type_list = ['str', 'bool', 'float', 'integer', 'enum', 'file']

def check_str(value, *args):
    return isinstance(value, str)

def check_bool(value, *args):
    return isinstance(value, bool)

def check_float(value, *args):
    return isinstance(value, float)

def check_integer(value, *args):
    return isinstance(value, int)

def check_enum(value, *args):
    return value in args[0]

def check_file(value, *args):
    return True

check_func_map = {
    'str': check_str,
    'bool': check_bool,
    'float': check_float,
    'integer': check_integer,
    'enum': check_enum,
    'file': check_file,
}

assert len(set(option_type_list) - set(check_func_map.keys())) == 0, f'选项与检查函数不匹配'

class Option:
    def __init__(self, name=None, name_tag=None, type='str', required=False, desc=None, default=None, enums=None):
        self._name = name  # 参数名称
        self._name_tag = name_tag  # 参数的前端显示名称(前端显示用,例如如果name为"path",则name_tag为"路径")
        self._type = type  # 参数类型,参考option_type_list
        self._required = required  # 是否必填
        self._desc = desc  # 参数描述
        self._default = default  # 参数默认值
        self._enums = enums  # enum类型的待选列表,如果type为enum类型则此参数必须填写

        assert self._type in option_type_list, f'{self._name} 选项类型未知'
        if self._type == 'enum':    
            assert isinstance(self._enums, list), f'{self._name} 选项参数 enums不为列表'
            assert self._enums, f'{self._name} 选项类型为 enum，但是未找到 enums'
            if self._default is not None:
                assert self._default in self._enums, f'{self._name} 选项默认值不在 enums 中'

    def to_dict(self):
        return {
            'name': self._name,
            'name_tag': self._name_tag,
            'type': self._type,
            'required': self._required,
            'desc': self._desc,
            'default': self._default,
            'enums': self._enums,
        }

    def is_valid(self, value):
        check_func = check_func_map[self._type]
        return check_func(value, self._enums)


def options_to_dict(options_list: list):
    options = {}
    try:
        if not options_list:
            return {}
        for option in options_list:
            options[option._name] = option.to_dict()
        return options
    except Exception as E:
        logger.error(E)
        return {}