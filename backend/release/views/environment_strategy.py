# -*- coding: utf-8 -*-
"""
环境策略视图
"""
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from utils.custom_model_viewSet import CustomModelViewSet
from ..models import EnvironmentStrategy
from ..serializers import EnvironmentStrategySerializer, EnvironmentStrategyCreateSerializer
from ..filters import EnvironmentStrategyFilter


class EnvironmentStrategyViewSet(CustomModelViewSet):
    """环境策略管理"""
    queryset = EnvironmentStrategy.objects.all()
    serializer_class = EnvironmentStrategySerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = EnvironmentStrategyFilter
    search_fields = ["name", "code", "description"]
    ordering_fields = ["create_time", "name"]
    enable_soft_delete = True

    action_serializers = {
        "create": EnvironmentStrategyCreateSerializer,
        "update": EnvironmentStrategyCreateSerializer,
    }

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.enable_soft_delete:
            queryset = queryset.filter(is_deleted=False)
        return queryset

    def perform_create(self, serializer):
        """创建时自动设置创建人"""
        # 如果设置为默认策略，先取消其他同环境策略的默认标记
        if serializer.validated_data.get('is_default'):
            EnvironmentStrategy.objects.filter(
                environment=serializer.validated_data.get('environment'),
                is_default=True
            ).update(is_default=False)
        serializer.save(creator=self.request.user.username)

    def perform_update(self, serializer):
        """更新时自动设置修改人"""
        instance = serializer.instance
        # 如果设置为默认策略，先取消其他同环境策略的默认标记
        if serializer.validated_data.get('is_default'):
            EnvironmentStrategy.objects.filter(
                environment=instance.environment,
                is_default=True
            ).exclude(id=instance.id).update(is_default=False)
        serializer.save(modifier=self.request.user.username)

    @action(detail=False, methods=['get'])
    def by_environment(self, request):
        """按环境获取策略列表"""
        environment = request.query_params.get('environment')
        if not environment:
            return Response({'code': 1, 'message': '请指定环境参数'}, status=status.HTTP_400_BAD_REQUEST)
        
        queryset = self.get_queryset().filter(environment=environment)
        serializer = self.get_serializer(queryset, many=True)
        return Response({'code': 0, 'data': serializer.data})

    @action(detail=False, methods=['get'])
    def defaults(self, request):
        """获取各环境的默认策略"""
        queryset = self.get_queryset().filter(is_default=True)
        serializer = self.get_serializer(queryset, many=True)
        return Response({'code': 0, 'data': serializer.data})

    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        """设置为默认策略"""
        strategy = self.get_object()
        
        # 取消同环境其他策略的默认标记
        EnvironmentStrategy.objects.filter(
            environment=strategy.environment,
            is_default=True
        ).exclude(id=strategy.id).update(is_default=False)
        
        # 设置当前策略为默认
        strategy.is_default = True
        strategy.save()
        
        return Response({'code': 0, 'message': '已设置为默认策略'})
