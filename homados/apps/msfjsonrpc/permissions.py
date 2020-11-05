from rest_framework.permissions import BasePermission


class CanUpdateModConfig(BasePermission):
    """
    是否有权限更新模块配置
    """

    def has_object_permission(self, request, view, obj):
        return bool(obj.user == request.user or obj.is_public == True)
