from rest_framework import serializers
import chardet


class BinaryTextField(serializers.Field):
    """获取以 BinaryField 存储的文本"""
    def to_internal_value(self, data):
        return data.encode()

    def to_representation(self, obj):
        data_bytes = obj.tobytes()
        result = chardet.detect(data_bytes)
        return data_bytes.decode(result['encoding'])
