from rest_framework import generics
from django_filters import rest_framework as filters
from .models import Modules


class ModuleFilter(filters.FilterSet):
    class Meta:
        model = Modules
        fields = {
            'type': ['exact'],
            'platform': ['icontains'],
            'arch': ['icontains'],
        }
