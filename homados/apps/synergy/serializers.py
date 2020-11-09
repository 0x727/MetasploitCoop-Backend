from rest_framework import serializers

from . import models


class ChatRecordSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username')

    """聊天记录序列化器"""
    class Meta:
        model = models.ChatRecord
        fields = ('username', 'user', 'message', 'room', 'created_at')
        read_only_fields = ('username', 'created_at')
