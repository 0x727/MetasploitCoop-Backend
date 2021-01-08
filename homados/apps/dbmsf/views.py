import datetime
from dateutil import parser
from django.contrib.postgres.aggregates.general import StringAgg
from django.db.models.aggregates import Min
from rest_framework.decorators import action
from homados.contrib.mymixins import PackResponseMixin
from rest_framework import filters, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from libs.utils import memview_to_str
from . import utils

from .models import (Event, Loot, MetasploitCredentialCore, ModuleResult,
                     Session, SessionEvent, Host)
from .serializers import (EventSerializer, LootSerializer,
                          MetasploitCredentialCoreSerializer,
                          ModuleResultSerializer, SessionEventSerializer,
                          SessionSerializer, HostSerializer)


class SessionViewSet(PackResponseMixin, viewsets.ModelViewSet):
    queryset = Session.objects.all()
    serializer_class = SessionSerializer
    permission_classes = [IsAuthenticated]

    @action(methods=['GET'], detail=True, url_path='events')
    def session_events(self, request, *args, **kwargs):
        """获取会话事件"""
        session = self.get_object()
        return Response(utils.get_session_events(session))

    @action(methods=['GET'], detail=True, url_path='modResults')
    def module_results(self, request, *args, **kwargs):
        """获取会话的模块执行结果"""
        session = self.get_object()
        return Response(utils.get_module_results(session))

    @action(methods=['GET'], detail=True, url_path='history')
    def history(self, request, *args, **kwargs):
        session = self.get_object()
        data = utils.get_session_events(session)
        data.extend(utils.get_module_results(session))
        data.sort(key=utils.sort_history_key)
        return Response(data)


class SessionEventViewSet(PackResponseMixin, viewsets.ReadOnlyModelViewSet):
    queryset = SessionEvent.objects.all()
    serializer_class = SessionEventSerializer
    permission_classes = [IsAuthenticated]


class ModuleResultViewSet(PackResponseMixin, viewsets.ReadOnlyModelViewSet):
    queryset = ModuleResult.objects.all()
    serializer_class = ModuleResultSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    lookup_field = 'track_uuid'

    def retrieve(self, request, *args, **kwargs):
        track_uuid = kwargs[self.lookup_field]
        results = self.get_queryset().filter(track_uuid=track_uuid).order_by('id')
        serializer = self.get_serializer(results, many=True)
        return Response(serializer.data)


class MetasploitCredentialCoreViewSet(PackResponseMixin, viewsets.ModelViewSet):
    queryset = MetasploitCredentialCore.objects.all()
    serializer_class = MetasploitCredentialCoreSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.OrderingFilter]

    def create(self, request, *args, **kwargs):
        print(request)
        print("Creating")
        super().create(request, *args, **kwargs)


class EventViewSet(PackResponseMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Event.objects.all()
    serializer_class = EventSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.OrderingFilter]


class LootViewSet(PackResponseMixin, viewsets.ModelViewSet):
    queryset = Loot.objects.all()
    serializer_class = LootSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.OrderingFilter]


class HostViewSet(PackResponseMixin, viewsets.ModelViewSet):
    queryset = Host.objects.all()
    serializer_class = HostSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.OrderingFilter]

    @action(methods=['GET'], detail=True, url_path='sessions')
    def sessions(self, request, *args, **kwargs):
        """获取主机关联的会话"""
        host = self.get_object()
        serializer = SessionSerializer(host.sessions, many=True)
        return Response(serializer.data)
