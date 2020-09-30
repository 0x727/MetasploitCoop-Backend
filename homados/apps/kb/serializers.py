from django.db.models import fields
from rest_framework import serializers
from homados.contrib.fields import MyJSONField

from kb.models import MsfModuleManual, TranslationBase


class MsfModuleManualSerializer(serializers.ModelSerializer):
    options = MyJSONField(ensure_ascii=False, allow_null=True, default=None)

    class Meta:
        model = MsfModuleManual
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class TranslationBaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = TranslationBase
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']
