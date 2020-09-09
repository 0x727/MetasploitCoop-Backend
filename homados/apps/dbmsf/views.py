from .models import Session, SessionEvent
from .serializers import SessionSerializer, SessionEventSerializer
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
