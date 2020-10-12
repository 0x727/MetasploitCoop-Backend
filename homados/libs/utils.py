import threading
import chardet
from django.conf import settings
from rest_framework.exceptions import ValidationError
from userauth.serializers import LogSerializer

logger = settings.LOGGER


class Singleton(type):
    """单例模式基类"""
    _lock = threading.Lock()
    def __init__(self, *args, **kwargs):
        self.__instance = None
        super().__init__(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        if self.__instance is None:
            with Singleton._lock:
                if self.__instance is None:
                    self.__instance = super().__call__(*args, **kwargs)
        return self.__instance

    def __new__(cls, *args, **kwargs):
        instance = type.__new__(cls, *args, **kwargs)
        return instance


def get_user_ident(user):
    """获取用户身份"""
    return getattr(user, 'username', '') or getattr(user, 'email', '')


def report_event(msg, data=None, ltype='default', level='info', callback=None):
    """事件报告写入日志"""
    try:
        data = {
            'ltype': ltype,
            'info': {
                'msg': msg,
                'data': data,
            },
            'level': level,
        }
        serializer = LogSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        if callback and callable(callback):
            callable(data)
    except ValidationError as e:
        logger.error(f'写入日志错误: {e}')

def report_auth_event(msg, callback=None):
    report_event(msg, ltype='auth', callback=callback)

def report_msfjob_event(msg, callback=None):
    report_event(msg, ltype='msfjob', callback=callback)

def memview_to_str(data):
    data_bytes = data.tobytes()
    result = chardet.detect(data_bytes)
    return data_bytes.decode(result['encoding'])