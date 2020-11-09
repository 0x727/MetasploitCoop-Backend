from django.db.models import fields
from rest_framework import serializers
from homados.contrib.fields import MyJSONField
from homados.contrib.serializers import MyModelSerializer

from kb.models import ContextMenu, MsfModuleManual, TranslationBase, FocusKeyword, ResourceScript


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


class ContextMenuMiniSerializer(MyModelSerializer):
    """只包含关键信息的右键菜单"""
    addition = MyJSONField(ensure_ascii=False, allow_null=True, default=None)

    class Meta:
        model = ContextMenu
        fields = ('id', 'text', 'addition', 'pid')


class ResourceScriptSerializer(serializers.ModelSerializer):
    """资源脚本表序列化器"""
    def validate_filename(self, value):
        if value.endswith('.rc') and len(value) > len('.rc'):
            return value
        raise serializers.ValidationError('资源脚本文件名必须以.rc结尾')

    class Meta:
        model = ResourceScript
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class ResourceScriptMiniSerializer(serializers.ModelSerializer):
    """资源脚本表精简信息序列化器"""
    class Meta:
        model = ResourceScript
        exclude = ('created_at', 'updated_at', 'description', 'content')
