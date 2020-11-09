from django_filters import rest_framework as filters
from . import models


class ChatRecordFilter(filters.FilterSet):
    class Meta:
        model = models.ChatRecord
        fields = ['room']
