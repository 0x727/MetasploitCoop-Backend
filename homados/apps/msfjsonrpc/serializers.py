from rest_framework import serializers
from . import models


class ModuleSerializer(serializers.ModelSerializer):
    aliases = serializers.ListField()
    author = serializers.ListField()
    references = serializers.ListField()
    targets = serializers.ListField()
    class Meta:
        model = models.Modules
        exclude = ['info_html', 'compatible_payloads']


class ModAutoConfigSerializer(serializers.ModelSerializer):
    def validate_config(self, value):
        if not value:
            raise serializers.ValidationError("配置 config 不能为空")
        return value

    class Meta:
        model = models.ModAutoConfig
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class ModAutoConfigMiniSerializer(serializers.ModelSerializer):
    """模块自动配置的精简信息"""
    class Meta:
        model = models.ModAutoConfig
        fields = ('id', 'config', 'is_public', 'is_enabled')
