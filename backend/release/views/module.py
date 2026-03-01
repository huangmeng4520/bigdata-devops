# -*- coding: utf-8 -*-
"""
模块管理视图
"""
import logging
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from utils.custom_model_viewSet import CustomModelViewSet
from ..models import Module, Application, SyncLog
from ..serializers import ModuleSerializer, ModuleCreateSerializer, ApplicationSerializer
from ..filters import ModuleFilter
from ..services import GitLabService, DevOpsException

logger = logging.getLogger(__name__)


class ModuleViewSet(CustomModelViewSet):
    """模块管理"""
    queryset = Module.objects.all()
    serializer_class = ModuleSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = ModuleFilter
    search_fields = ["name", "code"]
    ordering_fields = ["sort", "create_time"]
    enable_soft_delete = True

    action_serializers = {
        "create": ModuleCreateSerializer,
        "update": ModuleCreateSerializer,
    }

    def get_queryset(self):
        queryset = super().get_queryset().select_related("project")
        if self.enable_soft_delete:
            queryset = queryset.filter(is_deleted=False)
        return queryset

    def perform_create(self, serializer):
        """创建模块并自动创建 GitLab Subgroup"""
        instance = serializer.save(creator=self.request.user.username)
        self._create_gitlab_subgroup(instance)

    def _create_gitlab_subgroup(self, module: Module):
        """
        创建 GitLab Subgroup

        Args:
            module: Module 实例
        """
        # 检查项目是否有 GitLab Group ID
        if not module.project.gitlab_group_id:
            logger.warning(f"模块 {module.name} 所属项目没有 GitLab Group ID，跳过 Subgroup 创建")
            # 记录日志
            SyncLog.objects.create(
                project=module.project,
                module=module,
                sync_type="gitlab",
                resource_name=module.code,
                action="create",
                status=0,
                message="所属项目没有 GitLab Group ID"
            )
            return

        try:
            gitlab = GitLabService()
            result = gitlab.create_group(
                name=module.name,
                path=module.code,
                parent_id=module.project.gitlab_group_id,
                description=module.description
            )

            # 更新 GitLab Subgroup ID
            module.gitlab_subgroup_id = result.get("id")
            module.save(update_fields=["gitlab_subgroup_id"])

            # 记录同步日志
            SyncLog.objects.create(
                project=module.project,
                module=module,
                sync_type="gitlab",
                resource_name=f"{module.project.code}/{module.code}",
                action="create",
                status=1,
                message=f"创建 GitLab Subgroup 成功: {result.get('web_url', '')}"
            )

            logger.info(f"模块 {module.name} GitLab Subgroup 创建成功: {result.get('id')}")

        except DevOpsException as e:
            logger.error(f"模块 {module.name} GitLab Subgroup 创建失败: {e.message}")
            SyncLog.objects.create(
                project=module.project,
                module=module,
                sync_type="gitlab",
                resource_name=module.code,
                action="create",
                status=0,
                message=e.message
            )
        except Exception as e:
            logger.exception(f"模块 {module.name} GitLab Subgroup 创建异常: {e}")

    def perform_update(self, serializer):
        """更新时自动设置修改人"""
        serializer.save(modifier=self.request.user.username)

    @action(detail=True, methods=["get"])
    def applications(self, request, pk=None):
        """获取模块下的应用列表"""
        module = self.get_object()
        applications = Application.objects.filter(
            module=module, is_deleted=False
        ).select_related("project")
        serializer = ApplicationSerializer(applications, many=True)
        return Response({"code": 0, "data": serializer.data})

    @action(detail=False, methods=["get"])
    def by_project(self, request):
        """按项目分组获取模块列表"""
        project_id = request.query_params.get("project_id")
        if not project_id:
            return Response({"code": 1, "message": "缺少project_id参数"})

        modules = Module.objects.filter(
            project_id=project_id, is_deleted=False, status=1
        )
        serializer = ModuleSerializer(modules, many=True)
        return Response({"code": 0, "data": serializer.data})

    @action(detail=True, methods=["post"])
    def sync_gitlab(self, request, pk=None):
        """手动同步 GitLab Subgroup"""
        module = self.get_object()

        if module.gitlab_subgroup_id:
            return Response({
                "code": 1,
                "message": "GitLab Subgroup 已存在，请使用更新功能"
            })

        if not module.project.gitlab_group_id:
            return Response({
                "code": 1,
                "message": "所属项目没有 GitLab Group ID，请先同步项目"
            })

        self._create_gitlab_subgroup(module)
        module.refresh_from_db()

        return Response({
            "code": 0,
            "message": "同步成功" if module.gitlab_subgroup_id else "同步失败，请查看日志",
            "data": {"gitlab_subgroup_id": module.gitlab_subgroup_id}
        })

    @action(detail=True, methods=["get"])
    def sync_logs(self, request, pk=None):
        """获取模块的同步日志"""
        module = self.get_object()
        from ..serializers import SyncLogSerializer

        logs = SyncLog.objects.filter(module=module).order_by("-create_time")[:50]
        serializer = SyncLogSerializer(logs, many=True)
        return Response({"code": 0, "data": serializer.data})
