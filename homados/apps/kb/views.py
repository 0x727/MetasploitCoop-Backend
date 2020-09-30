from django_filters import rest_framework as rich_filters
from homados.contrib.exceptions import MissParamError
from homados.contrib.mymixins import PackResponseMixin
from rest_framework import exceptions, filters, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from kb.filters import MsfModuleManualFilter
from kb.models import MsfModuleManual, TranslationBase
from kb.serializers import MsfModuleManualSerializer, TranslationBaseSerializer

# Create your views here.


class MsfModuleManualViewSet(PackResponseMixin, viewsets.ModelViewSet):
    queryset = MsfModuleManual.objects.all()
    serializer_class = MsfModuleManualSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [rich_filters.DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = MsfModuleManualFilter


class TranslationBaseViewSet(PackResponseMixin, viewsets.ModelViewSet):
    queryset = TranslationBase.objects.all()
    serializer_class = TranslationBaseSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['en_source', 'zh_target']

    @action(methods=['POST'], detail=False, url_path='getOne')
    def get_translation(self, request, *args, **kwargs):
        try:
            en_source = request.data['en_source'].strip()
            translation_base = self.get_queryset().filter(en_source=en_source).first()
            if not translation_base:
                raise exceptions.NotFound
            return Response(data=translation_base.zh_target)
        except KeyError as e:
            raise MissParamError(query_params=['en_source'])
