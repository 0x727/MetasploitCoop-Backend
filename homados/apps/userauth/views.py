import json

from django.conf import settings
from django.contrib import auth
from django.contrib.auth.models import AnonymousUser, User
from homados.contrib.cache import ConfigCache
from homados.contrib.exceptions import MissParamError
from homados.contrib.mymixins import PackResponseMixin
from libs.utils import get_user_ident, report_auth_event
from rest_framework import exceptions, filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Log
from .serializers import LogSerializer, UserRegisterSerializer, UserSerializer

# 平台运行时配置
runtime_config = ConfigCache()


class AuthViewSet(PackResponseMixin, viewsets.ModelViewSet):
    """auth viewset"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    @action(methods=["POST"], detail=False, url_path="register", permission_classes=[])
    def register(self, request, *args, **kwargs):
        if runtime_config.get('close_register'):
            raise exceptions.ValidationError(detail={'detail': '该平台已关闭注册'})
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
        return Response('登出平台成功')
    
    @action(methods=["GET"], detail=False, url_path="info")
    def info(self, request, *args, **kwargs):
        data = {}
        data['roles'] = ['admin'] if request.user.is_staff else ['user']
        serializer = self.get_serializer(request.user)
        report_auth_event(f"{get_user_ident(request.user)} 进入平台")
        data['close_register'] = runtime_config.get('close_register', False)
        data.update(serializer.data)
        return Response(data)

    def list(self, request):
        queryset = User.objects.all()
        serializer = UserSerializer(queryset, many=True)
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(data={'detail': f'{instance.username} 删除成功'})
    
    def update(self, request, *args, **kwargs):
        try:
            user = User.objects.get(username=self.get_object())
            if(request.data['password']==request.data['confirm_password']):
                user.set_password(request.data.get('password'))
                user.save()
                return Response({'detail': '修改密码成功'})
            else:
                return Response({'detail': 'The two password inputs are not the same'})
        except KeyError as e:
            raise MissParamError(query_params=[str(e)])


    @action(methods=["PATCH"], detail=False, url_path="switchRegister")
    def switch_register(self, request, *args, **kwargs):
        try:
            is_close_register = bool(request.data['close'])
            runtime_config.set('close_register', is_close_register, None)
            msg = '关闭' if is_close_register else '打开'
            report_auth_event(f"{get_user_ident(request.user)} {msg}注册")
            return Response({'detail': '设置成功'})
        except KeyError as e:
            raise MissParamError(query_params=['close'])


class LogViewSet(PackResponseMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Log.objects.all()
    serializer_class = LogSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['info', 'ltype']
