# -*- coding: utf-8 -*-
"""
应用管理视图
"""
import logging
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from utils.custom_model_viewSet import CustomModelViewSet
from ..models import Application, ConfigPackage, SyncLog
from ..serializers import (
    ApplicationSerializer, ApplicationCreateSerializer,
    ConfigPackageSerializer, SyncLogSerializer
)
from ..filters import ApplicationFilter
from ..services import GitLabService, DevOpsException
from ..tasks import create_gitlab_resources, create_jenkins_resources, create_harbor_resources, generate_config_package

logger = logging.getLogger(__name__)


class ApplicationViewSet(CustomModelViewSet):
    """应用管理"""
    queryset = Application.objects.all()
    serializer_class = ApplicationSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = ApplicationFilter
    search_fields = ["name", "code"]
    ordering_fields = ["sort", "create_time"]
    enable_soft_delete = True

    action_serializers = {
        "create": ApplicationCreateSerializer,
        "update": ApplicationCreateSerializer,
    }

    def get_queryset(self):
        queryset = super().get_queryset().select_related("project", "module")
        if self.enable_soft_delete:
            queryset = queryset.filter(is_deleted=False)
        return queryset

    def perform_create(self, serializer):
        """创建应用并自动创建相关资源"""
        instance = serializer.save(creator=self.request.user.username)
        self._create_resources(instance)

    def _create_resources(self, app: Application):
        """
        创建应用相关资源

        1. GitLab Project (同步创建，获取 git_url)
        2. Jenkins CI/CD Jobs (异步)
        3. Harbor Project (异步)

        Args:
            app: Application 实例
        """
        # 检查模块是否有 GitLab Subgroup ID
        if not app.module.gitlab_subgroup_id:
            logger.warning(f"应用 {app.name} 所属模块没有 GitLab Subgroup ID，跳过资源创建")
            SyncLog.objects.create(
                project=app.project,
                module=app.module,
                app=app,
                sync_type="gitlab",
                resource_name=app.code,
                action="create",
                status=0,
                message="所属模块没有 GitLab Subgroup ID"
            )
            return

        # 1. 同步创建 GitLab Project
        gitlab_project_id = self._create_gitlab_project(app)

        if not gitlab_project_id:
            logger.error(f"应用 {app.name} GitLab Project 创建失败，跳过后续资源创建")
            return

        # 2. 异步创建 Jenkins 和 Harbor 资源
        try:
            # Jenkins 异步任务
            create_jenkins_resources.delay(app.id)
            logger.info(f"应用 {app.name} Jenkins 资源创建任务已提交")

            # Harbor 异步任务
            create_harbor_resources.delay(app.id)
            logger.info(f"应用 {app.name} Harbor 资源创建任务已提交")

        except Exception as e:
            logger.exception(f"应用 {app.name} 异步任务提交失败: {e}")

    def _create_gitlab_project(self, app: Application) -> int:
        """
        创建 GitLab Project

        Args:
            app: Application 实例

        Returns:
            GitLab Project ID 或 None
        """
        try:
            gitlab = GitLabService()
            result = gitlab.create_project(
                name=app.name,
                path=app.code,
                namespace_id=app.module.gitlab_subgroup_id,
                description=app.description
            )

            # 更新应用
            app.gitlab_project_id = result.get("id")
            app.git_url = result.get("ssh_url_to_repo") or result.get("http_url_to_repo")
            app.save(update_fields=["gitlab_project_id", "git_url"])

            # 记录日志
            SyncLog.objects.create(
                project=app.project,
                module=app.module,
                app=app,
                sync_type="gitlab",
                resource_name=result.get("path_with_namespace", app.code),
                action="create",
                status=1,
                message=f"创建 GitLab Project 成功: {result.get('web_url', '')}"
            )

            logger.info(f"应用 {app.name} GitLab Project 创建成功: {result.get('id')}")
            return result.get("id")

        except DevOpsException as e:
            logger.error(f"应用 {app.name} GitLab Project 创建失败: {e.message}")
            SyncLog.objects.create(
                project=app.project,
                module=app.module,
                app=app,
                sync_type="gitlab",
                resource_name=app.code,
                action="create",
                status=0,
                message=e.message
            )
            return None
        except Exception as e:
            logger.exception(f"应用 {app.name} GitLab Project 创建异常: {e}")
            return None

    def perform_update(self, serializer):
        """更新时自动设置修改人"""
        serializer.save(modifier=self.request.user.username)

    @action(detail=True, methods=["get"])
    def config_packages(self, request, pk=None):
        """获取应用的配置包列表"""
        app = self.get_object()
        packages = ConfigPackage.objects.filter(app=app, is_deleted=False)
        serializer = ConfigPackageSerializer(packages, many=True)
        return Response({"code": 0, "data": serializer.data})

    @action(detail=True, methods=["get"])
    def sync_logs(self, request, pk=None):
        """获取应用的同步日志"""
        app = self.get_object()
        logs = SyncLog.objects.filter(app=app).order_by("-create_time")[:50]
        serializer = SyncLogSerializer(logs, many=True)
        return Response({"code": 0, "data": serializer.data})

    @action(detail=True, methods=["post"])
    def generate_config(self, request, pk=None):
        """生成配置包"""
        app = self.get_object()
        version = request.data.get("version")

        # 异步生成配置包
        task = generate_config_package.delay(app.id, version)

        return Response({
            "code": 0,
            "message": f"应用 {app.name} 配置包生成任务已提交",
            "data": {"task_id": task.id}
        })

    @action(detail=True, methods=["post"])
    def sync_resources(self, request, pk=None):
        """手动同步所有资源"""
        app = self.get_object()
        resource_type = request.data.get("type", "all")

        results = {}

        if resource_type in ["all", "gitlab"]:
            if not app.gitlab_project_id and app.module.gitlab_subgroup_id:
                task = create_gitlab_resources.delay(app.id)
                results["gitlab"] = {"task_id": task.id}
            else:
                results["gitlab"] = {"skipped": True, "reason": "exists or no_subgroup"}

        if resource_type in ["all", "jenkins"]:
            if not app.jenkins_ci_job and app.git_url:
                task = create_jenkins_resources.delay(app.id)
                results["jenkins"] = {"task_id": task.id}
            else:
                results["jenkins"] = {"skipped": True, "reason": "exists or no_git_url"}

        if resource_type in ["all", "harbor"]:
            if not app.harbor_project:
                task = create_harbor_resources.delay(app.id)
                results["harbor"] = {"task_id": task.id}
            else:
                results["harbor"] = {"skipped": True, "reason": "exists"}

        return Response({
            "code": 0,
            "message": "资源同步任务已提交",
            "data": results
        })

    @action(detail=True, methods=["get"])
    def resource_status(self, request, pk=None):
        """获取应用资源创建状态"""
        app = self.get_object()

        return Response({
            "code": 0,
            "data": {
                "gitlab": {
                    "project_id": app.gitlab_project_id,
                    "git_url": app.git_url,
                    "status": "created" if app.gitlab_project_id else "pending"
                },
                "jenkins": {
                    "ci_job": app.jenkins_ci_job,
                    "cd_job": app.jenkins_cd_job,
                    "status": "created" if app.jenkins_ci_job else "pending"
                },
                "harbor": {
                    "project": app.harbor_project,
                    "status": "created" if app.harbor_project else "pending"
                }
            }
        })
