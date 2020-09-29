from django.db.models import fields
from rest_framework import generics
from django_filters import rest_framework as filters

from kb.models import MsfModuleManual


class MsfModuleManualFilter(filters.FilterSet):
    fullname = filters.CharFilter(field_name="fullname", lookup_expr='icontains')
    title = filters.CharFilter(field_name="title", lookup_expr='icontains')
    intro = filters.CharFilter(field_name="intro", lookup_expr='icontains')

    class Meta:
        model = MsfModuleManual
        fields = ['fullname', 'title', 'intro']
