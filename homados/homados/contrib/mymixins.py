# 存放一些自定义的minix类
from rest_framework.response import Response
from rest_framework import status
from django.http import FileResponse


class PackResponseMixin:
    """包装drf框架的response以适应前端

    需要添加到第一个继承类，主要原因为python多继承的方法调用顺序，For Example:
    class ProjectViewSet(myminixs.PackResponseMixin, viewsets.ModelViewSet):
        pass
    覆盖了finalize_response方法来返回
    """

    def finalize_response(self, request, response, *args, **kwargs):
        """包装response返回"""
        if isinstance(response, FileResponse):
            return response
        message = ''
        if 200 <= response.status_code < 300:
            code = 20000
        else:
            message = response.data
            code = 20000 + response.status_code
        response = Response({'code': code, 'data': response.data, 'message': message}, status=response.status_code)
        return super().finalize_response(request, response, *args, **kwargs)
