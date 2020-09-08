from rest_framework import exceptions
from django.conf import settings
from rest_framework import status


logger = settings.LOGGER


class UnknownError(exceptions.APIException):
    def __init__(self):
        msg = '出现未知错误，请联系管理员'
        logger.exception(msg)
        super().__init__(detail=msg, code=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MSFJSONRPCError(exceptions.APIException):
    def __init__(self):
        msg = 'msfjsonrpc出错'
        logger.exception(msg)
        super().__init__(detail=msg, code=status.HTTP_502_BAD_GATEWAY)


class MissParamError(exceptions.ValidationError):
    def __init__(self, body_params: list=None, query_params: list=None):
        data = {}
        if body_params:
            for param in body_params:
                data[param] = '此 body 参数是必须的'
        if query_params:
            for param in query_params:
                data[param] = '此 query 参数是必须的'
        super().__init__(detail=data)

