from rest_framework import serializers
import chardet
from libs.utils import memview_to_str


class BinaryTextField(serializers.Field):
    """获取以 BinaryField 存储的文本"""
    def to_internal_value(self, data):
        return data.encode()

    def to_representation(self, obj):
        return memview_to_str(obj)
