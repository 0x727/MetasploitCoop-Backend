from django_filters import rest_framework as rich_filters
from rest_framework import filters, viewsets
from rest_framework.permissions import IsAuthenticated

from kb.filters import MsfModuleManualFilter
from kb.models import MsfModuleManual
from kb.serializers import MsfModuleManualSerializer

# Create your views here.


class MsfModuleManualViewSet(viewsets.ModelViewSet):
    queryset = MsfModuleManual.objects.all()
    serializer_class = MsfModuleManualSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [rich_filters.DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = MsfModuleManualFilter
