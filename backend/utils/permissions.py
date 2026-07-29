from rest_framework import permissions
from rest_framework.permissions import BasePermission
from system.models import Menu
from utils.string_utils import camel_to_snake


class IsSuperUserOrReadOnly(BasePermission):
    """超级用户可读写，普通用户只读"""
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_superuser



class HasButtonPermission(BasePermission):
    """
    通用按钮权限校验
    用法：在视图中设置 required_permission = 'xxx:xxx:xxx'
    """
    def has_permission(self, request, view):
        required_code = getattr(view, 'required_permission', None)
        if not required_code:
            # 自动推断：类名转蛇形（CodeRepository -> code_repository），与前端按钮码（下划线）一致
            app_label = view.queryset.model._meta.app_label
            model_name = camel_to_snake(view.queryset.model.__name__)
            action = getattr(view, 'action', None)
            action_map = {
                'create': 'create',
                'update': 'edit',
                'partial_update': 'edit',
                'destroy': 'delete',
                'list': 'query',
                'retrieve': 'query',
            }
            if action in action_map:
                required_code = f"{app_label}:{model_name}:{action_map[action]}"
        if not required_code:
            return True  # 不需要按钮权限
        user = request.user
        if not user.is_authenticated or user.is_anonymous:
            return False
        if user.is_superuser:
            return True
        # 同时兼容下划线/连字符模型名，避免历史按钮码不一致导致误拦
        codes = [required_code]
        if '_' in required_code:
            codes.append(required_code.replace('_', '-'))
        if '-' in required_code:
            codes.append(required_code.replace('-', '_'))
        # 系统中未登记该权限码按钮时不做拦截（如辅助类自定义 action），仅要求登录
        if not Menu.objects.filter(type='button', auth_code__in=codes).exists():
            return True
        role_ids = user.role.values_list('id', flat=True)
        return Menu.objects.filter(
            type='button',
            role__id__in=role_ids,
            auth_code__in=codes
        ).exists()


class HasMutateButtonPermission(HasButtonPermission):
    """
    仅对写操作（create/update/destroy 等非安全方法）校验按钮权限，
    读操作（list/retrieve）放行，避免影响列表、下拉等查询路径造成回归。
    用法：在视图中设置 permission_classes = [HasMutateButtonPermission]
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return super().has_permission(request, view)
