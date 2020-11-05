from django.db.models import fields
from rest_framework import serializers
from homados.contrib.fields import MyJSONField
from homados.contrib.serializers import MyModelSerializer

from kb.models import ContextMenu, MsfModuleManual, TranslationBase, FocusKeyword


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


class FocusKeywordSerializer(serializers.ModelSerializer):
    class Meta:
        model = FocusKeyword
        exclude = ['created_at', 'updated_at']


class ContextMenuSerializer(MyModelSerializer):
    """右键菜单"""
    addition = MyJSONField(ensure_ascii=False, allow_null=True, default=None)

    class Meta:
        model = ContextMenu
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']
