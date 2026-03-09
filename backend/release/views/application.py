# -*- coding: utf-8 -*-
"""
应用管理视图
"""
import logging
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from utils.custom_model_viewSet import CustomModelViewSet
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
        queryset = super().get_queryset().select_related("project", "module", "ci_template", "cd_template")
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
        """更新时自动设置修改人，并检查是否需要同步到 Jenkins"""
        instance = serializer.instance
        old_ci_template = instance.ci_template_id
        old_cd_template = instance.cd_template_id
        old_ci_variables = instance.ci_variables
        old_cd_variables = instance.cd_variables

        serializer.save(modifier=self.request.user.username)

        # 检查 CI/CD 配置是否变更
        instance.refresh_from_db()
        ci_changed = (
            old_ci_template != instance.ci_template_id or
            old_ci_variables != instance.ci_variables
        )
        cd_changed = (
            old_cd_template != instance.cd_template_id or
            old_cd_variables != instance.cd_variables
        )

        # 如果配置变更且有关联模板，自动同步到 Jenkins
        if (ci_changed or cd_changed) and (instance.ci_template or instance.cd_template):
            logger.info(f"应用 {instance.name} CI/CD 配置变更，触发 Jenkins 同步")
            sync_application_jenkins.delay(instance.id)

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
            if not app.jenkins_ci_job or app.jenkins_sync_status == 3 or force:
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

        if app.jenkins_ci_job and app.jenkins_sync_status != 3 and not force:
            return Response({
                "code": 1,
                "message": "Jenkins Job 已存在，如需重新创建请使用 force=true"
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
                    "ci_job": app.jenkins_ci_job,
                    "cd_job": app.jenkins_cd_job,
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
        手动同步 CI/CD 配置到 Jenkins

        将关联的 CI/CD 模板同步到 Jenkins Job
        """
        app = self.get_object()

        # 检查是否有关联模板
        if not app.ci_template and not app.cd_template:
            return Response({
                "code": 1,
                "message": "请先关联 CI 或 CD 模板"
            }, status=400)

        # 触发异步同步任务
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
                "ci_template": app.ci_template.name if app.ci_template else None,
                "cd_template": app.cd_template.name if app.cd_template else None,
            }
        })

    @action(detail=True, methods=["get"])
    def preview_jenkinsfile(self, request, pk=None):
        """预览生成的 Jenkinsfile"""
        from ..services import JenkinsService

        app = self.get_object()
        template_type = request.query_params.get("type", "ci")  # ci 或 cd

        template = app.ci_template if template_type == "ci" else app.cd_template
        variables = app.ci_variables if template_type == "ci" else app.cd_variables

        if not template:
            return Response({
                "code": 1,
                "message": f"未关联 {template_type.upper()} 模板"
            }, status=400)

        # 获取最新版本
        latest_version = template.latest_version
        if not latest_version:
            return Response({
                "code": 1,
                "message": "模板没有可用版本"
            }, status=400)

        # 合并变量
        content = latest_version.content
        template_variables = latest_version.variables or {}

        # 先替换模板默认变量
        if template_variables and isinstance(template_variables, dict):
            for var in template_variables.get('variables', []):
                var_name = var.get('name')
                if var_name and var_name not in variables:
                    variables[var_name] = var.get('default', '')

        # 替换用户变量
        for key, value in variables.items():
            content = content.replace(f'${{{key}}}', str(value))

        return Response({
            "code": 0,
            "data": {
                "content": content,
                "template_name": template.name,
                "template_version": latest_version.version,
                "variables": variables,
            }
        })
