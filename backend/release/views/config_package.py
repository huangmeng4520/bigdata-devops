# -*- coding: utf-8 -*-
"""
配置包管理视图
"""
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from utils.custom_model_viewSet import CustomModelViewSet
from utils.data_permission import DataPermissionMixin
from utils.permissions import HasMutateButtonPermission
from ..models import ConfigPackage
from ..serializers import ConfigPackageSerializer
from ..filters import ConfigPackageFilter


class ConfigPackageViewSet(DataPermissionMixin, CustomModelViewSet):
    """配置包管理"""
    queryset = ConfigPackage.objects.all()
    serializer_class = ConfigPackageSerializer
    permission_classes = [HasMutateButtonPermission]
    filter_backends = [DjangoFilterBackend]
    filterset_class = ConfigPackageFilter
    search_fields = ["version"]
    ordering_fields = ["create_time"]
    enable_soft_delete = True

    # 数据权限：按所属应用→项目级联隔离
    scope_type = 'project'
    scope_field = 'app__project_id'

    def get_queryset(self):
        queryset = super().get_queryset().select_related("app")
        if self.enable_soft_delete:
            queryset = queryset.filter(is_deleted=False)
        return self.data_permission_filter(queryset)

    def perform_create(self, serializer):
        """创建时自动设置创建人"""
        serializer.save(creator=self.request.user.username)

    def perform_update(self, serializer):
        self.check_object_data_permission(serializer.instance)
        serializer.save(modifier=self.request.user.username)

    def perform_destroy(self, instance):
        self.check_object_data_permission(instance)
        super().perform_destroy(instance)

    @action(detail=True, methods=["get"])
    def sync_logs(self, request, pk=None):
        """获取配置包的同步日志"""
        from ..models import SyncLog
        from ..serializers import SyncLogSerializer

        package = self.get_object()
        logs = SyncLog.objects.filter(config_package=package).order_by("-create_time")
        serializer = SyncLogSerializer(logs, many=True)
        return Response({"code": 0, "data": serializer.data})

    @action(detail=True, methods=["post"])
    def sync(self, request, pk=None):
        """触发同步"""
        # TODO: 实现同步逻辑
        package = self.get_object()
        return Response({
            "code": 0,
            "message": f"配置包 {package.version} 同步任务已提交"
        })
