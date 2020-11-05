from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers
import copy
from libs.utils import memview_to_str


class BinaryTextField(serializers.Field):
    """获取以 BinaryField 存储的文本"""
    def to_internal_value(self, data):
        return data.encode()

    def to_representation(self, obj):
        return memview_to_str(obj)


class PrimaryKeyRelatedField(serializers.PrimaryKeyRelatedField):
    """主要是为了避免当外键为0这种情况的发生，比如树状表"""
    def to_internal_value(self, data):
        if self.pk_field is not None:
            data = self.pk_field.to_internal_value(data)
        try:
            return self.get_queryset().get(pk=data)
        except ObjectDoesNotExist:
            return self.get_queryset().model(pk=0)
        except (TypeError, ValueError):
            self.fail('incorrect_type', data_type=type(data).__name__)


class MyModelSerializer(serializers.ModelSerializer):
    """树状表适用的model serializer（不检查外键存在与否）"""
    serializer_related_field = PrimaryKeyRelatedField
