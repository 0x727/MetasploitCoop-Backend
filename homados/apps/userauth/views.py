from django.contrib import auth
from django.contrib.auth.models import User
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from homados.contrib.mymixins import PackResponseMixin

from .serializers import UserRegisterSerializer, UserSerializer

# Create your views here.


class AuthViewSet(PackResponseMixin, viewsets.GenericViewSet):
    """auth viewset"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    @action(methods=["POST"], detail=False, url_path="register", permission_classes=[])
    def register(self, request, *args, **kwargs):
        serializer = UserRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(methods=["POST"], detail=False, url_path="login", permission_classes=[])
    def login(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        user = auth.authenticate(request, username=serializer.initial_data["username"], password=serializer.initial_data["password"])
        auth.login(request, user)
        serializer = self.get_serializer(user)
        return Response({**serializer.data, 'token': request.session.session_key})
    
    @action(methods=["DELETE"], detail=False, url_path="logout")
    def logout(self, request, *args, **kwargs):
        auth.logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)
