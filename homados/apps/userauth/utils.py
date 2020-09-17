from django.conf import settings
from rest_framework.exceptions import ValidationError

from .serializers import LogSerializer

logger = settings.LOGGER


def report_event(msg, ltype='default', callback=None):
    """事件报告写入日志"""
    try:
        data = {
            'ltype': ltype,
            'info': {
                'data': msg,
            },
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
