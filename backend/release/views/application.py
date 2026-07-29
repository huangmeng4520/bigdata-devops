# -*- coding: utf-8 -*-
"""
应用管理视图
"""
import logging
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from utils.custom_model_viewSet import CustomModelViewSet
from utils.data_permission import DataPermissionMixin
from utils.permissions import HasMutateButtonPermission
from ..models import Application, ConfigPackage, SyncLog, PipelineTemplate
from ..serializers import (
    ApplicationSerializer, ApplicationCreateSerializer,
    ConfigPackageSerializer, SyncLogSerializer
)
from ..filters import ApplicationFilter
from ..services import GitLabService, DevOpsException
from ..tasks import (
    create_gitlab_resources, create_jenkins_resources, create_harbor_resources,
    generate_config_package, sync_application_jenkins
)

logger = logging.getLogger(__name__)


class ApplicationViewSet(DataPermissionMixin, CustomModelViewSet):
    """应用管理"""
    queryset = Application.objects.all()
    serializer_class = ApplicationSerializer
    permission_classes = [HasMutateButtonPermission]
    filter_backends = [DjangoFilterBackend]
    filterset_class = ApplicationFilter
    search_fields = ["name", "code"]
    ordering_fields = ["sort", "create_time"]
    enable_soft_delete = True

    # 数据权限：应用归属项目，按 project 级联隔离
    scope_type = 'project'
    scope_field = 'project_id'

    action_serializers = {
        "create": ApplicationCreateSerializer,
        "update": ApplicationCreateSerializer,
    }

    def get_queryset(self):
        queryset = super().get_queryset().select_related("project", "module")
        if self.enable_soft_delete:
            queryset = queryset.filter(is_deleted=False)
        return self.data_permission_filter(queryset)

    def perform_create(self, serializer):
        """创建应用（不自动创建 GitLab 仓库，兼容一个 Git 仓库多个应用）"""
        instance = serializer.save(creator=self.request.user.username)
        # 创建人自动获得该应用的数据权限（中央关联表）
        from system.models import DataPermissionRule
        DataPermissionRule.objects.get_or_create(
            scope_type='project',
            scope_id=instance.project_id,
            user=self.request.user,
            defaults={'creator': self.request.user.username, 'level': 'owner'},
        )
        try:
            create_jenkins_resources.delay(instance.id)
            create_harbor_resources.delay(instance.id)
        except Exception as e:
            logger.exception(f"应用 {instance.name} 异步任务提交失败: {e}")

    def perform_update(self, serializer):
        """更新时自动设置修改人"""
        self.check_object_data_permission(serializer.instance)
        serializer.save(modifier=self.request.user.username)

    def perform_destroy(self, instance):
        """删除前校验数据权限"""
        self.check_object_data_permission(instance)
        super().perform_destroy(instance)

    def _create_resources(self, app: Application):
        """
        创建应用相关资源（包含 GitLab，已废弃）

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
        self._create_jenkins_and_harbor(app)

    def _create_gitlab_project(self, app: Application) -> int:
        """
        创建 GitLab Project

        Args:
            app: Application 实例

        Returns:
            GitLab Project ID 或 None
        """
        from django.utils import timezone

        try:
            app.gitlab_sync_status = 1
            app.save(update_fields=['gitlab_sync_status'])

            gitlab = GitLabService()
            result = gitlab.create_project(
                name=app.name,
                path=app.code,
                namespace_id=app.module.gitlab_subgroup_id,
                description=app.description
            )

            app.gitlab_project_id = result.get("id")
            app.git_url = result.get("ssh_url_to_repo") or result.get("http_url_to_repo")
            app.gitlab_sync_status = 2
            app.gitlab_sync_time = timezone.now()
            app.gitlab_sync_message = "创建成功"
            app.save(update_fields=["gitlab_project_id", "git_url", "gitlab_sync_status", "gitlab_sync_time", "gitlab_sync_message"])

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
            app.gitlab_sync_status = 3
            app.gitlab_sync_message = e.message
            app.save(update_fields=['gitlab_sync_status', 'gitlab_sync_message'])
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
            app.gitlab_sync_status = 3
            app.gitlab_sync_message = str(e)[:512]
            app.save(update_fields=['gitlab_sync_status', 'gitlab_sync_message'])
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
        force = request.data.get("force", False)

        results = {}

        if resource_type in ["all", "gitlab"]:
            if not app.gitlab_project_id or app.gitlab_sync_status == 3 or force:
                task = create_gitlab_resources.delay(app.id, force)
                results["gitlab"] = {"task_id": task.id}
            else:
                results["gitlab"] = {"skipped": True, "reason": "exists or no_subgroup"}

        if resource_type in ["all", "jenkins"]:
            if app.jenkins_sync_status != 2 or force:
                if app.git_url:
                    task = create_jenkins_resources.delay(app.id, force)
                    results["jenkins"] = {"task_id": task.id}
                else:
                    results["jenkins"] = {"skipped": True, "reason": "no_git_url"}
            else:
                results["jenkins"] = {"skipped": True, "reason": "exists"}

        if resource_type in ["all", "harbor"]:
            if not app.harbor_project or app.harbor_sync_status == 3 or force:
                task = create_harbor_resources.delay(app.id, force)
                results["harbor"] = {"task_id": task.id}
            else:
                results["harbor"] = {"skipped": True, "reason": "exists"}

        return Response({
            "code": 0,
            "message": "资源同步任务已提交",
            "data": results
        })

    @action(detail=True, methods=["post"])
    def sync_gitlab(self, request, pk=None):
        """手动同步 GitLab 资源"""
        app = self.get_object()
        force = request.data.get("force", False)

        if not app.module.gitlab_subgroup_id:
            return Response({
                "code": 1,
                "message": "所属模块没有 GitLab Subgroup ID，无法创建 GitLab 项目"
            }, status=400)

        if app.gitlab_project_id and app.gitlab_sync_status != 3 and not force:
            return Response({
                "code": 1,
                "message": "GitLab 项目已存在，如需重新创建请使用 force=true"
            }, status=400)

        task = create_gitlab_resources.delay(app.id, force)

        return Response({
            "code": 0,
            "message": "GitLab 同步任务已提交",
            "data": {"task_id": task.id}
        })

    @action(detail=True, methods=["post"])
    def sync_jenkins(self, request, pk=None):
        """手动同步 Jenkins 资源"""
        app = self.get_object()
        force = request.data.get("force", False)

        if not app.git_url:
            return Response({
                "code": 1,
                "message": "应用没有 Git 仓库地址，无法创建 Jenkins Job"
            }, status=400)

        if app.jenkins_sync_status == 2 and not force:
            return Response({
                "code": 1,
                "message": "Jenkins 资源已同步，如需重新创建请使用 force=true"
            }, status=400)

        task = create_jenkins_resources.delay(app.id, force)

        return Response({
            "code": 0,
            "message": "Jenkins 同步任务已提交",
            "data": {"task_id": task.id}
        })

    @action(detail=True, methods=["post"])
    def sync_harbor(self, request, pk=None):
        """手动同步 Harbor 资源"""
        app = self.get_object()
        force = request.data.get("force", False)

        if app.harbor_project and app.harbor_sync_status != 3 and not force:
            return Response({
                "code": 1,
                "message": "Harbor 项目已存在，如需重新创建请使用 force=true"
            }, status=400)

        task = create_harbor_resources.delay(app.id, force)

        return Response({
            "code": 0,
            "message": "Harbor 同步任务已提交",
            "data": {"task_id": task.id}
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
                    "status": app.get_gitlab_sync_status_display(),
                    "sync_status": app.gitlab_sync_status,
                    "sync_time": app.gitlab_sync_time,
                    "sync_message": app.gitlab_sync_message,
                },
                "jenkins": {
                    "status": app.get_jenkins_sync_status_display(),
                    "sync_status": app.jenkins_sync_status,
                    "sync_time": app.jenkins_sync_time,
                    "sync_message": app.jenkins_sync_message,
                },
                "harbor": {
                    "project": app.harbor_project,
                    "status": app.get_harbor_sync_status_display(),
                    "sync_status": app.harbor_sync_status,
                    "sync_time": app.harbor_sync_time,
                    "sync_message": app.harbor_sync_message,
                }
            }
        })

    @action(detail=True, methods=["post"])
    def sync_to_jenkins(self, request, pk=None):
        """
        手动同步 Pipeline 配置到 Jenkins
        """
        from ..models import ApplicationPipelineConfig

        app = self.get_object()

        has_configs = ApplicationPipelineConfig.objects.filter(
            application=app, is_deleted=False
        ).exists()

        if not has_configs:
            return Response({
                "code": 1,
                "message": "请先配置 Pipeline 模板"
            }, status=400)

        task = sync_application_jenkins.delay(app.id)

        return Response({
            "code": 0,
            "message": "Jenkins 同步任务已提交",
            "data": {"task_id": task.id}
        })

    @action(detail=True, methods=["get"])
    def jenkins_sync_status(self, request, pk=None):
        """获取 Jenkins 同步状态"""
        app = self.get_object()

        return Response({
            "code": 0,
            "data": {
                "sync_status": app.jenkins_sync_status,
                "sync_status_display": app.get_jenkins_sync_status_display(),
                "sync_time": app.jenkins_sync_time,
                "sync_message": app.jenkins_sync_message,
            }
        })

    @action(detail=True, methods=["get"])
    def preview_jenkinsfile(self, request, pk=None):
        """预览生成的 Jenkinsfile"""
        from ..models import ApplicationPipelineConfig

        app = self.get_object()
        env_id = request.query_params.get("environment")

        configs = ApplicationPipelineConfig.objects.filter(
            application=app, is_deleted=False
        )
        if env_id:
            configs = configs.filter(environment_id=env_id)

        config = configs.first()
        if not config or not config.template:
            return Response({
                "code": 1,
                "message": "未关联 Pipeline 模板"
            }, status=400)

        template = config.template
        variables = config.variables or {}
        latest_version = template.latest_version
        if not latest_version:
            return Response({
                "code": 1,
                "message": "模板没有可用版本"
            }, status=400)

        content = latest_version.content
        template_variables = latest_version.variables or {}
        if template_variables and isinstance(template_variables, dict):
            for var in template_variables.get('variables', []):
                var_name = var.get('name')
                if var_name and var_name not in variables:
                    variables[var_name] = var.get('default', '')

        for key, value in variables.items():
            content = content.replace(f'${{{key}}}', str(value))

        return Response({
            "code": 0,
            "data": {
                "content": content,
                "template_name": template.name,
                "template_version": latest_version.version,
                "variables": variables,
                "environment": config.environment.name if config.environment else None,
            }
        })
