# -*- coding: utf-8 -*-
"""
项目管理视图
"""
import logging
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from utils.custom_model_viewSet import CustomModelViewSet
from ..models import Project, Module, Application, SyncLog
from ..serializers import ProjectSerializer, ProjectCreateSerializer, ModuleSerializer, ApplicationSerializer
from ..filters import ProjectFilter
from ..services import GitLabService, DevOpsException

logger = logging.getLogger(__name__)


class ProjectViewSet(CustomModelViewSet):
    """项目管理"""
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = ProjectFilter
    search_fields = ["name", "code"]
    ordering_fields = ["sort", "create_time"]
    enable_soft_delete = True

    action_serializers = {
        "create": ProjectCreateSerializer,
        "update": ProjectCreateSerializer,
    }

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.enable_soft_delete:
            queryset = queryset.filter(is_deleted=False)
        return queryset

    def perform_create(self, serializer):
        """创建项目并自动创建 GitLab Group"""
        instance = serializer.save(creator=self.request.user.username)
        self._create_gitlab_group(instance)

    def _create_gitlab_group(self, project: Project):
        """
        创建 GitLab Group

        Args:
            project: Project 实例
        """
        try:
            gitlab = GitLabService()
            result = gitlab.create_group(
                name=project.name,
                path=project.code,
                description=project.description
            )

            # 更新 GitLab Group ID
            project.gitlab_group_id = result.get("id")
            project.save(update_fields=["gitlab_group_id"])

            # 记录同步日志
            SyncLog.objects.create(
                project=project,
                sync_type="gitlab",
                resource_name=project.code,
                action="create",
                status=1,
                message=f"创建 GitLab Group 成功: {result.get('web_url', '')}"
            )

            logger.info(f"项目 {project.name} GitLab Group 创建成功: {result.get('id')}")

        except DevOpsException as e:
            logger.error(f"项目 {project.name} GitLab Group 创建失败: {e.message}")
            # 记录失败日志，但不阻塞主流程
            SyncLog.objects.create(
                project=project,
                sync_type="gitlab",
                resource_name=project.code,
                action="create",
                status=0,
                message=e.message
            )
        except Exception as e:
            logger.exception(f"项目 {project.name} GitLab Group 创建异常: {e}")

    def perform_update(self, serializer):
        """更新时自动设置修改人"""
        serializer.save(modifier=self.request.user.username)

    @action(detail=True, methods=["get"])
    def modules(self, request, pk=None):
        """获取项目下的模块列表"""
        project = self.get_object()
        modules = Module.objects.filter(project=project, is_deleted=False)
        serializer = ModuleSerializer(modules, many=True)
        return Response({"code": 0, "data": serializer.data})

    @action(detail=True, methods=["get"])
    def applications(self, request, pk=None):
        """获取项目下的应用列表"""
        project = self.get_object()
        applications = Application.objects.filter(
            project=project, is_deleted=False
        ).select_related("module")
        serializer = ApplicationSerializer(applications, many=True)
        return Response({"code": 0, "data": serializer.data})

    @action(detail=False, methods=["get"])
    def tree(self, request):
        """获取项目-模块-应用树形结构"""
        projects = Project.objects.filter(is_deleted=False, status=1)
        result = []
        for project in projects:
            modules = Module.objects.filter(project=project, is_deleted=False, status=1)
            module_list = []
            for module in modules:
                applications = Application.objects.filter(
                    module=module, is_deleted=False, status=1
                ).values("id", "name", "code", "app_type")
                module_list.append({
                    "id": module.id,
                    "name": module.name,
                    "code": module.code,
                    "applications": list(applications)
                })
            result.append({
                "id": project.id,
                "name": project.name,
                "code": project.code,
                "gitlab_group_id": project.gitlab_group_id,
                "modules": module_list
            })
        return Response({"code": 0, "data": result})

    @action(detail=True, methods=["post"])
    def sync_gitlab(self, request, pk=None):
        """手动同步 GitLab Group"""
        project = self.get_object()

        if project.gitlab_group_id:
            return Response({
                "code": 1,
                "message": "GitLab Group 已存在，请使用更新功能"
            })

        self._create_gitlab_group(project)
        project.refresh_from_db()

        return Response({
            "code": 0,
            "message": "同步成功" if project.gitlab_group_id else "同步失败，请查看日志",
            "data": {"gitlab_group_id": project.gitlab_group_id}
        })

    @action(detail=True, methods=["get"])
    def sync_logs(self, request, pk=None):
        """获取项目的同步日志"""
        project = self.get_object()
        from ..serializers import SyncLogSerializer

        logs = SyncLog.objects.filter(project=project).order_by("-create_time")[:50]
        serializer = SyncLogSerializer(logs, many=True)
        return Response({"code": 0, "data": serializer.data})
