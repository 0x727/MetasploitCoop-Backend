from django.contrib import auth
from django.contrib.auth.models import AnonymousUser, User
from rest_framework import exceptions, filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from homados.contrib.mymixins import PackResponseMixin
from libs.utils import get_user_ident, report_auth_event

from .models import Log
from .serializers import LogSerializer, UserRegisterSerializer, UserSerializer


class AuthViewSet(PackResponseMixin, viewsets.GenericViewSet):
    """auth viewset"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    @action(methods=["POST"], detail=False, url_path="register", permission_classes=[])
    def register(self, request, *args, **kwargs):
        serializer = UserRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        report_auth_event(f"{get_user_ident(user)} 注册成功")
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(methods=["POST"], detail=False, url_path="login", permission_classes=[])
    def login(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        user = auth.authenticate(request, username=serializer.initial_data["username"], password=serializer.initial_data["password"])
        if not user:
            raise exceptions.PermissionDenied(detail='账号或密码错误')
        auth.login(request, user)
        serializer = self.get_serializer(user)
        report_auth_event(f"{get_user_ident(user)} 登录平台")
        return Response({**serializer.data, 'token': request.session.session_key})
    
    @action(methods=["DELETE"], detail=False, url_path="logout")
    def logout(self, request, *args, **kwargs):
        auth.logout(request)
        report_auth_event(f"{get_user_ident(request.user)} 登出平台")
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(methods=["GET"], detail=False, url_path="info")
    def info(self, request, *args, **kwargs):
        data = {}
        data['roles'] = ['admin'] if request.user.is_staff else ['user']
        serializer = self.get_serializer(request.user)
        report_auth_event(f"{get_user_ident(request.user)} 进入平台")
        data.update(serializer.data)
        return Response(data)

class LogViewSet(PackResponseMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Log.objects.all()
    serializer_class = LogSerializer
    permission_class = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['info', 'ltype']
