from . import constants

def check_valid_plugin(obj):
    """检查模块是否可用"""
    for attr in constants.REQUIRED_ATTRS:
        assert hasattr(obj, attr), f'{obj} payload 模块必须含有 {attr} 属性'