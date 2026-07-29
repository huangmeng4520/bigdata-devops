# -*- coding: utf-8 -*-
"""
通用数据权限引擎（可复用，不局限于应用模块）

设计要点
--------
1. 角色数据范围 ``Role.data_scope``：``all`` / ``custom`` / ``dept`` / ``self``，
   属于角色属性，与具体业务无关，任何模块都适用。
2. 用户与数据资源的关联统一存储在中央表 ``system_data_permission_rule``
   （``DataPermissionRule``）。新增业务模块只需约定一个 ``scope_type`` 字符串，
   往该表写入 ``(scope_type, scope_id, user)`` 即可，无需改动表结构。
3. 任意需要做数据隔离的 ViewSet 继承 ``DataPermissionMixin``，声明两个类属性即可：
   - ``scope_type``：资源类型标识（如 ``'application'``）。
   - ``scope_field``：本模型到范围资源的关联字段（如 ``'app_id'``）；
     ``None`` 表示该模型**全局可读**（如流水线模板、项目/模块下拉）。
4. 创建人可见：``custom`` / ``dept`` 范围下，自动并入「创建人为本人的资源」
   （依赖各模型继承自 ``CoreModel`` 的 ``creator`` 字段）。

未来模块复用示例
----------------
    class Alert(CoreModel):
        members = ...   # 无需此字段，引擎按中央表 + creator 工作
        ...

    class AlertViewSet(DataPermissionMixin, CustomModelViewSet):
        scope_type = 'alert'      # 一行接入数据权限
        scope_field = 'id'
"""
from rest_framework.exceptions import PermissionDenied

# 数据范围常量
DATA_SCOPE_ALL = 'all'
DATA_SCOPE_CUSTOM = 'custom'
DATA_SCOPE_DEPT = 'dept'
DATA_SCOPE_SELF = 'self'

# scope_type -> 模型，用于「创建人可见」等通用逻辑
SCOPE_MODELS = {}
_registered = False


def register_scope_model(scope_type, model):
    SCOPE_MODELS[scope_type] = model


def ensure_scope_models():
    """惰性注册内置 scope 模型，避免循环导入。"""
    global _registered
    if _registered:
        return
    from release.models import Application, Project
    register_scope_model('application', Application)
    register_scope_model('project', Project)
    _registered = True


def resolve_data_scope(user):
    """返回用户最广的数据范围。多个角色取最高优先级：all > custom > dept > self。"""
    if getattr(user, 'is_superuser', False):
        return DATA_SCOPE_ALL
    scopes = set(user.role.values_list('data_scope', flat=True))
    if not scopes:
        return DATA_SCOPE_SELF
    if DATA_SCOPE_ALL in scopes:
        return DATA_SCOPE_ALL
    if DATA_SCOPE_CUSTOM in scopes:
        return DATA_SCOPE_CUSTOM
    if DATA_SCOPE_DEPT in scopes:
        return DATA_SCOPE_DEPT
    return DATA_SCOPE_SELF


def get_allowed_scope_ids(user, scope_type):
    """
    返回用户在该 scope_type 下可访问的资源主键集合；
    返回 ``None`` 表示不限制（全部可见）。
    """
    ensure_scope_models()
    from system.models import DataPermissionRule, User

    scope = resolve_data_scope(user)
    if scope == DATA_SCOPE_ALL:
        return None

    rule_ids = set(
        DataPermissionRule.objects.filter(scope_type=scope_type, user=user)
        .values_list('scope_id', flat=True)
    )

    model = SCOPE_MODELS.get(scope_type)
    has_creator = model is not None and hasattr(model, 'creator')

    if scope == DATA_SCOPE_CUSTOM:
        if has_creator:
            rule_ids |= set(
                model.objects.filter(creator=user.username).values_list('id', flat=True)
            )
    elif scope == DATA_SCOPE_DEPT:
        dept_ids = set(user.dept.values_list('id', flat=True))
        user_names = set(
            User.objects.filter(dept__id__in=dept_ids).values_list('username', flat=True)
        )
        if has_creator and user_names:
            rule_ids |= set(
                model.objects.filter(creator__in=user_names).values_list('id', flat=True)
            )
    elif scope == DATA_SCOPE_SELF:
        if has_creator:
            rule_ids = set(
                model.objects.filter(creator=user.username).values_list('id', flat=True)
            )
        else:
            rule_ids = set()

    # 历史兼容：早期以 application 为范围单位的授权，其所属项目同样可见。
    # 统一迁移为 project 后可移除该段（见 migrate_data_permission_to_project 命令）。
    if scope_type == 'project':
        from system.models import DataPermissionRule as _Rule
        legacy_app_ids = set(
            _Rule.objects.filter(scope_type='application', user=user, is_deleted=False)
            .values_list('scope_id', flat=True)
        )
        if legacy_app_ids:
            from release.models import Application as _App
            legacy_project_ids = set(
                _App.objects.filter(id__in=list(legacy_app_ids))
                .values_list('project_id', flat=True)
            )
            rule_ids |= legacy_project_ids

    if not rule_ids:
        return set()
    return rule_ids


def user_has_scope_access(user, scope_type, scope_id):
    """判断用户是否可访问某条 scope 资源（用于自定义 action / 函数视图）。"""
    if scope_id is None:
        return False
    allowed = get_allowed_scope_ids(user, scope_type)
    if allowed is None:
        return True
    return scope_id in allowed


def user_has_button_perm(user, auth_code):
    """判断用户是否拥有某按钮权限（按 auth_code）。"""
    if getattr(user, 'is_superuser', False):
        return True
    from system.models import RolePermission
    return RolePermission.objects.filter(
        role__in=user.role.all(), menu__auth_code=auth_code
    ).exists()


def _resolve_field_path(instance, path):
    """按 ``a__b__c`` 逐级解析关联对象，返回末端属性值（支持 scope_field 关联路径）。"""
    obj = instance
    for part in path.split('__'):
        if obj is None:
            return None
        obj = getattr(obj, part, None)
    return obj


class DataPermissionMixin:
    """
    通用数据权限混合类。子类声明 ``scope_type`` / ``scope_field`` 即可接入。
    """

    scope_type = None
    scope_field = None  # None 表示全局可读，不做数据隔离

    def get_user(self):
        return self.request.user

    def data_permission_filter(self, queryset):
        if not self.scope_field:
            return queryset
        allowed = get_allowed_scope_ids(self.get_user(), self.scope_type)
        if allowed is None:
            return queryset
        if not allowed:
            return queryset.none()
        return queryset.filter(**{f"{self.scope_field}__in": allowed})

    def get_queryset(self):
        return self.data_permission_filter(super().get_queryset())

    def check_object_data_permission(self, instance):
        """写操作（update/destroy）前校验对象归属。"""
        if not self.scope_field:
            return
        allowed = get_allowed_scope_ids(self.get_user(), self.scope_type)
        if allowed is None:
            return
        if self.scope_field == 'id':
            obj_id = instance.id
        elif '__' in self.scope_field:
            obj_id = _resolve_field_path(instance, self.scope_field)
            if obj_id is not None and not isinstance(obj_id, int):
                obj_id = getattr(obj_id, 'id', None)
        else:
            obj_id = getattr(instance, self.scope_field, None)
            if obj_id is not None and not isinstance(obj_id, int):
                obj_id = getattr(obj_id, 'id', None)
        if obj_id not in allowed:
            raise PermissionDenied('无权限操作该数据：不在您的数据范围内')
