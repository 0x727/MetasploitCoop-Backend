from homados.contrib.mymixins import PackResponseMixin
from rest_framework import filters, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import (Event, Loot, MetasploitCredentialCore, ModuleResult,
                     Session, SessionEvent)
from .serializers import (EventSerializer, LootSerializer,
                          MetasploitCredentialCoreSerializer,
                          ModuleResultSerializer, SessionEventSerializer,
                          SessionSerializer)


class SessionViewSet(PackResponseMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Session.objects.all()
    serializer_class = SessionSerializer
    permission_classes = [IsAuthenticated]


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
