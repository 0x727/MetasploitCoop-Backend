from django.contrib.auth.models import User
from django.utils.timezone import now
from rest_framework import serializers

from .models import Log


class UserSerializer(serializers.ModelSerializer):
    """user model serialzier"""
    class Meta:
        model = User
        # fields = "__all__"
        exclude = ("is_superuser", "first_name", "last_name")
        read_only_fields = ["id"]
        extra_kwargs = {
            "password": {"write_only": True},
        }


class UserRegisterSerializer(serializers.ModelSerializer):
    """ user model serialzier for register"""
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        # fields = "__all__"
        exclude = ("is_superuser", "first_name", "last_name")
        read_only_fields = ["id", "is_staff"]
        extra_kwargs = {
            "password": {"write_only": True},
        }

    def validate(self, data):
        if data["password"] != data["confirm_password"]:
            raise serializers.ValidationError("The two password inputs are not the same")
        del data["confirm_password"]
        return data
    
    def create(self, validated_data):
        # 第一个注册用户为管理员
        user_count = User.objects.count()
        if user_count == 0:
            validated_data["is_staff"] = True
        user = super().create(validated_data)
        user.set_password(validated_data["password"])
        user.save()
        return user


class LogSerializer(serializers.ModelSerializer):
    info = serializers.JSONField()
    time_since_created = serializers.SerializerMethodField()

    class Meta:
        model = Log
        fields = '__all__'

    def get_time_since_created(self, obj):
        return (now() - obj.created).total_seconds()
