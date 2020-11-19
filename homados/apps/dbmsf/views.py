from django.contrib.postgres.aggregates.general import StringAgg
from django.db.models.aggregates import Min
from rest_framework.decorators import action
from homados.contrib.mymixins import PackResponseMixin
from rest_framework import filters, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from libs.utils import memview_to_str

from .models import (Event, Loot, MetasploitCredentialCore, ModuleResult,
                     Session, SessionEvent, Host)
from .serializers import (EventSerializer, LootSerializer,
                          MetasploitCredentialCoreSerializer,
                          ModuleResultSerializer, SessionEventSerializer,
                          SessionSerializer, HostSerializer)


class SessionViewSet(PackResponseMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Session.objects.all()
    serializer_class = SessionSerializer
    permission_classes = [IsAuthenticated]

    @action(methods=['GET'], detail=True, url_path='events')
    def session_events(self, request, *args, **kwargs):
        """获取会话事件"""
        session = self.get_object()
        data = []
        if session.session_events:
            serializer = SessionEventSerializer(session.session_events, many=True)
            data = serializer.data
        return Response(data)

    @action(methods=['GET'], detail=True, url_path='modResults')
    def module_results(self, request, *args, **kwargs):
        """获取会话的模块执行结果"""
        session = self.get_object()
        data = []
        if session.module_results:
            data = list(ModuleResult.objects.filter(session=session).values('track_uuid').annotate(
                output=StringAgg('output', delimiter=''),
                created_at=Min('created_at'),
                fullname=Min('fullname')
            ))
        for i in data:
            i['output'] = memview_to_str(i['output'])
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

class MetasploitCredentialCoreViewSet(PackResponseMixin, viewsets.ReadOnlyModelViewSet):
    queryset = MetasploitCredentialCore.objects.all()
    serializer_class = MetasploitCredentialCoreSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.OrderingFilter]


class EventViewSet(PackResponseMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Event.objects.all()
    serializer_class = EventSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.OrderingFilter]


class LootViewSet(PackResponseMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Loot.objects.all()
    serializer_class = LootSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.OrderingFilter]


class HostViewSet(PackResponseMixin, viewsets.ReadOnlyModelViewSet):
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
