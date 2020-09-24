from django.db.models import fields
from rest_framework import generics
from django_filters import rest_framework as filters
from .models import Modules


class ModuleFilter(filters.FilterSet):
    platform = filters.CharFilter(field_name="platform", lookup_expr='icontains')
    arch = filters.CharFilter(field_name="arch", lookup_expr='icontains')

    class Meta:
        model = Modules
        fields = ['type', 'platform', 'arch']
