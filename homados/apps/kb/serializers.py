from django.db.models import fields
from rest_framework import serializers

from kb.models import MsfModuleManual


class MsfModuleManualSerializer(serializers.ModelSerializer):
    class Meta:
        model = MsfModuleManual
        fields = '__all__'
