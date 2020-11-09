from django.db.models.aggregates import Count
from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django_filters import rest_framework as rich_filters
from rest_framework.response import Response

from homados.contrib.mymixins import PackResponseMixin
from synergy.filters import ChatRecordFilter
from synergy.models import ChatRecord
from synergy.serializers import ChatRecordSerializer

# Create your views here.


class ChatRecordViewSet(PackResponseMixin, viewsets.ReadOnlyModelViewSet):
    queryset = ChatRecord.objects.all()
    serializer_class = ChatRecordSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [rich_filters.DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = ChatRecordFilter

    @action(methods=['GET'], detail=False, url_path='rooms', pagination_class = None)
    def rooms(self, request, *args, **kwargs):
        data = self.get_queryset().values("room").annotate(total_pages=Count('messages'))
        return Response(data=data)
