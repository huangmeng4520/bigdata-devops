# -*- coding: utf-8 -*-
"""
数据权限规则（用户 <-> 数据资源）管理接口。

供前端「应用权限分配」页调用：将研发用户分配到具体应用（scope_type='application'）。
任意业务模块只需约定 scope_type 字符串即可复用同一套接口，无需改表结构。
"""
from django_filters import rest_framework as filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.response import Response

from system.models import DataPermissionRule, User
from utils.custom_model_viewSet import CustomModelViewSet
from utils.serializers import CustomModelSerializer


class DataPermissionRuleSerializer(CustomModelSerializer):
    """数据权限规则序列化器"""
    username = serializers.CharField(source='user.username', read_only=True)
    nickname = serializers.CharField(source='user.nickname', read_only=True)

    class Meta:
        model = DataPermissionRule
        fields = '__all__'
        read_only_fields = ['id', 'create_time', 'update_time']


class DataPermissionRuleFilter(filters.FilterSet):
    scope_type = filters.CharFilter(field_name='scope_type')
    scope_id = filters.NumberFilter(field_name='scope_id')
    user_id = filters.NumberFilter(field_name='user_id')
    level = filters.CharFilter(field_name='level')

    class Meta:
        model = DataPermissionRule
        fields = ['scope_type', 'scope_id', 'user_id', 'level']


class DataPermissionRuleViewSet(CustomModelViewSet):
    """数据权限规则管理（用户<->资源多对多分配）"""
    queryset = DataPermissionRule.objects.select_related('user').all()
    serializer_class = DataPermissionRuleSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = DataPermissionRuleFilter
    search_fields = ['user__username', 'user__nickname']
    ordering_fields = ['create_time']
    enable_soft_delete = False

    def get_required_permission(self):
        # 自定义动作复用基础权限码，避免为 assign/scope_users 额外建按钮
        if self.action == 'assign':
            return 'system:data_permission_rule:edit'
        if self.action in ('scope_users', 'user_scopes'):
            return 'system:data_permission_rule:query'
        return super().get_required_permission()

    @action(detail=False, methods=['get'])
    def scope_users(self, request):
        """列出某资源范围下被授予的用户（前端：选中应用后看已分配研发）"""
        scope_type = request.query_params.get('scope_type')
        scope_id = request.query_params.get('scope_id')
        if not scope_type or not scope_id:
            return Response(
                {'error': 'scope_type 和 scope_id 必填'},
                status=status.HTTP_400_BAD_REQUEST
            )
        rules = self.get_queryset().filter(scope_type=scope_type, scope_id=scope_id)
        data = [
            {
                'user_id': r.user_id,
                'username': r.user.username,
                'nickname': r.user.nickname,
                'level': r.level,
            }
            for r in rules
        ]
        return self._build_response(data=data, message='ok', status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def user_scopes(self, request):
        """反向查询：某用户被授予的资源范围列表（前端：按用户查看其应用）"""
        user_id = request.query_params.get('user_id')
        scope_type = request.query_params.get('scope_type')
        qs = self.get_queryset()
        if user_id:
            qs = qs.filter(user_id=user_id)
        if scope_type:
            qs = qs.filter(scope_type=scope_type)
        data = [
            {
                'scope_type': r.scope_type,
                'scope_id': r.scope_id,
                'level': r.level,
                'username': r.user.username,
                'nickname': r.user.nickname,
            }
            for r in qs
        ]
        return self._build_response(data=data, message='ok', status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def assign(self, request):
        """
        批量分配用户到某资源范围（覆盖式：替换该范围下原有分配）。

        body: {scope_type, scope_id, user_ids: [...], level?}
        适用于「应用权限分配」页的勾选保存：先删除该应用下的旧分配，再按勾选重建。
        """
        scope_type = request.data.get('scope_type')
        scope_id = request.data.get('scope_id')
        user_ids = request.data.get('user_ids', [])
        level = request.data.get('level', 'member')
        if not scope_type or not scope_id:
            return Response(
                {'error': 'scope_type 和 scope_id 必填'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if not isinstance(user_ids, list):
            return Response(
                {'error': 'user_ids 必须是数组'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 覆盖式：删除该范围下原有分配
        DataPermissionRule.objects.filter(scope_type=scope_type, scope_id=scope_id).delete()

        valid_users = User.objects.filter(id__in=user_ids)
        created_ids = []
        for user in valid_users:
            rule, _ = DataPermissionRule.objects.get_or_create(
                scope_type=scope_type,
                scope_id=scope_id,
                user=user,
                defaults={'level': level, 'creator': request.user.username},
            )
            created_ids.append(rule.id)
        return self._build_response(
            data={'count': len(created_ids)},
            message='ok',
            status=status.HTTP_200_OK
        )
