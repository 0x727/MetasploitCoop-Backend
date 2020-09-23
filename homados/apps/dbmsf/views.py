from .models import Session, SessionEvent, ModuleResult
from .serializers import SessionSerializer, SessionEventSerializer, ModuleResultSerializer
from homados.contrib.mymixins import PackResponseMixin
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated


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
    lookup_field = 'track_uuid'

    def retrieve(self, request, *args, **kwargs):
        track_uuid = kwargs[self.lookup_field]
        results = self.get_queryset().filter(track_uuid=track_uuid).order_by('id')
        serializer = self.get_serializer(results, many=True)
        return Response(serializer.data)
