# -*- coding: utf-8 -*-
"""
发布管理 Celery 异步任务
"""
import logging
from celery import shared_task
from django.db import transaction

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def create_gitlab_resources(self, app_id: int):
    """
    创建 GitLab 资源的异步任务

    Args:
        app_id: 应用 ID
    """
    from .models import Application, SyncLog
    from .services import GitLabService, DevOpsException

    logger.info(f"[Celery] 开始创建 GitLab 资源: app_id={app_id}")

    try:
        app = Application.objects.select_related("project", "module").get(pk=app_id)
    except Application.DoesNotExist:
        logger.error(f"[Celery] 应用不存在: app_id={app_id}")
        return {"success": False, "error": "应用不存在"}

    gitlab = GitLabService()

    try:
        # 如果已有 gitlab_project_id，跳过
        if app.gitlab_project_id:
            logger.info(f"[Celery] GitLab Project 已存在: {app.gitlab_project_id}")
            return {"success": True, "skipped": True, "reason": "project_exists"}

        # 获取 Subgroup ID
        subgroup_id = app.module.gitlab_subgroup_id
        if not subgroup_id:
            logger.warning(f"[Celery] 模块没有 GitLab Subgroup ID")
            return {"success": False, "error": "no_subgroup"}

        # 创建 Project
        project = gitlab.create_project(
            name=app.name,
            path=app.code,
            namespace_id=subgroup_id,
            description=app.description
        )

        # 更新应用
        with transaction.atomic():
            app.gitlab_project_id = project["id"]
            app.git_url = project.get("ssh_url_to_repo") or project.get("http_url_to_repo")
            app.save(update_fields=["gitlab_project_id", "git_url"])

        # 记录日志
        SyncLog.objects.create(
            app=app,
            project=app.project,
            module=app.module,
            sync_type="gitlab",
            resource_name=project["path_with_namespace"],
            action="create",
            status=1,
            message=f"创建 GitLab Project 成功: {project['web_url']}"
        )

        logger.info(f"[Celery] GitLab Project 创建成功: {project['id']}")
        return {"success": True, "project_id": project["id"]}

    except DevOpsException as e:
        logger.error(f"[Celery] GitLab 资源创建失败: {e.message}")

        # 记录失败日志
        SyncLog.objects.create(
            app_id=app_id,
            sync_type="gitlab",
            resource_name=app.code,
            action="create",
            status=0,
            message=e.message
        )

        # 重试
        raise self.retry(exc=e)
    except Exception as e:
        logger.exception(f"[Celery] GitLab 资源创建异常: {e}")
        return {"success": False, "error": str(e)}


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def create_jenkins_resources(self, app_id: int):
    """
    创建 Jenkins 资源的异步任务

    Args:
        app_id: 应用 ID
    """
    from .models import Application, SyncLog
    from .services import JenkinsService, DevOpsException

    logger.info(f"[Celery] 开始创建 Jenkins 资源: app_id={app_id}")

    try:
        app = Application.objects.select_related("project", "module").get(pk=app_id)
    except Application.DoesNotExist:
        logger.error(f"[Celery] 应用不存在: app_id={app_id}")
        return {"success": False, "error": "应用不存在"}

    jenkins = JenkinsService()

    try:
        # 如果已有 jenkins_ci_job，跳过
        if app.jenkins_ci_job:
            logger.info(f"[Celery] Jenkins Jobs 已存在: {app.jenkins_ci_job}")
            return {"success": True, "skipped": True, "reason": "jobs_exist"}

        # 检查 Git URL
        if not app.git_url:
            logger.warning(f"[Celery] 应用没有 Git URL")
            return {"success": False, "error": "no_git_url"}

        # 创建 CI/CD Jobs
        results = jenkins.create_ci_cd_jobs(
            project_code=app.project.code,
            module_code=app.module.code,
            app_code=app.code,
            git_url=app.git_url,
            branch=app.build_branch
        )

        # 更新应用
        with transaction.atomic():
            app.jenkins_ci_job = jenkins.get_job_full_name(
                app.project.code, app.module.code, app.code, "ci"
            )
            app.jenkins_cd_job = jenkins.get_job_full_name(
                app.project.code, app.module.code, app.code, "cd"
            )
            app.save(update_fields=["jenkins_ci_job", "jenkins_cd_job"])

        # 记录日志
        SyncLog.objects.create(
            app=app,
            project=app.project,
            module=app.module,
            sync_type="jenkins",
            resource_name=f"{app.jenkins_ci_job}, {app.jenkins_cd_job}",
            action="create",
            status=1,
            message=f"创建 Jenkins CI/CD Jobs 成功: CI={results['ci']}, CD={results['cd']}"
        )

        logger.info(f"[Celery] Jenkins Jobs 创建成功")
        return {"success": True, "results": results}

    except DevOpsException as e:
        logger.error(f"[Celery] Jenkins 资源创建失败: {e.message}")

        SyncLog.objects.create(
            app_id=app_id,
            sync_type="jenkins",
            resource_name=app.code,
            action="create",
            status=0,
            message=e.message
        )

        raise self.retry(exc=e)
    except Exception as e:
        logger.exception(f"[Celery] Jenkins 资源创建异常: {e}")
        return {"success": False, "error": str(e)}


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def create_harbor_resources(self, app_id: int):
    """
    创建 Harbor 资源的异步任务

    Args:
        app_id: 应用 ID
    """
    from .models import Application, SyncLog
    from .services import HarborService, DevOpsException

    logger.info(f"[Celery] 开始创建 Harbor 资源: app_id={app_id}")

    try:
        app = Application.objects.select_related("project", "module").get(pk=app_id)
    except Application.DoesNotExist:
        logger.error(f"[Celery] 应用不存在: app_id={app_id}")
        return {"success": False, "error": "应用不存在"}

    harbor = HarborService()

    try:
        # 如果已有 harbor_project，跳过
        if app.harbor_project:
            logger.info(f"[Celery] Harbor Project 已存在: {app.harbor_project}")
            return {"success": True, "skipped": True, "reason": "project_exists"}

        # 创建 Harbor Project（使用 project_code-module_code 作为名称）
        project_name = f"{app.project.code}-{app.module.code}"
        project = harbor.create_project(project_name)

        # 更新应用
        with transaction.atomic():
            app.harbor_project = project_name
            app.save(update_fields=["harbor_project"])

        # 记录日志
        SyncLog.objects.create(
            app=app,
            project=app.project,
            module=app.module,
            sync_type="harbor",
            resource_name=project_name,
            action="create",
            status=1,
            message=f"创建 Harbor Project 成功: {project_name}"
        )

        logger.info(f"[Celery] Harbor Project 创建成功: {project_name}")
        return {"success": True, "project_name": project_name}

    except DevOpsException as e:
        logger.error(f"[Celery] Harbor 资源创建失败: {e.message}")

        SyncLog.objects.create(
            app_id=app_id,
            sync_type="harbor",
            resource_name=app.code,
            action="create",
            status=0,
            message=e.message
        )

        raise self.retry(exc=e)
    except Exception as e:
        logger.exception(f"[Celery] Harbor 资源创建异常: {e}")
        return {"success": False, "error": str(e)}


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def generate_config_package(self, app_id: int, version: str = None):
    """
    生成配置包的异步任务

    Args:
        app_id: 应用 ID
        version: 版本号
    """
    from .models import Application, ConfigPackage, SyncLog
    from .services import ConfigPackageService, DevOpsException

    logger.info(f"[Celery] 开始生成配置包: app_id={app_id}")

    try:
        app = Application.objects.select_related("project", "module").get(pk=app_id)
    except Application.DoesNotExist:
        logger.error(f"[Celery] 应用不存在: app_id={app_id}")
        return {"success": False, "error": "应用不存在"}

    service = ConfigPackageService()

    try:
        # 生成配置包
        result = service.generate_package(app_id, version)

        # 保存到数据库
        ConfigPackage.objects.create(
            app=app,
            version=result["version"],
            file_path=result["file_path"],
            file_size=result["file_size"],
            checksum=result["checksum"],
            sync_status=0  # 待同步
        )

        # 记录日志
        SyncLog.objects.create(
            app=app,
            project=app.project,
            module=app.module,
            sync_type="ansible",  # 配置包同步
            resource_name=result["file_name"],
            action="create",
            status=1,
            message=f"生成配置包成功: {result['file_name']}"
        )

        logger.info(f"[Celery] 配置包生成成功: {result['file_name']}")
        return {"success": True, **result}

    except DevOpsException as e:
        logger.error(f"[Celery] 配置包生成失败: {e.message}")

        SyncLog.objects.create(
            app_id=app_id,
            sync_type="ansible",
            resource_name=str(app_id),
            action="create",
            status=0,
            message=e.message
        )

        raise self.retry(exc=e)
    except Exception as e:
        logger.exception(f"[Celery] 配置包生成异常: {e}")
        return {"success": False, "error": str(e)}


@shared_task
def sync_all_resources(app_id: int):
    """
    同步所有资源的组合任务

    按顺序创建：GitLab -> Jenkins -> Harbor

    Args:
        app_id: 应用 ID
    """
    from celery import chain

    logger.info(f"[Celery] 开始同步所有资源: app_id={app_id}")

    # 使用 chain 按顺序执行
    workflow = chain(
        create_gitlab_resources.s(app_id),
        create_jenkins_resources.s(app_id),
        create_harbor_resources.s(app_id)
    )

    result = workflow.apply_async()
    return {"task_id": result.id}


@shared_task
def test_all_connections():
    """
    测试所有外部系统连接
    """
    from .services import GitLabService, JenkinsService, HarborService

    results = {
        "gitlab": False,
        "jenkins": False,
        "harbor": False
    }

    try:
        gitlab = GitLabService()
        results["gitlab"] = gitlab.test_connection()
    except Exception as e:
        logger.error(f"GitLab 连接测试失败: {e}")

    try:
        jenkins = JenkinsService()
        results["jenkins"] = jenkins.test_connection()
    except Exception as e:
        logger.error(f"Jenkins 连接测试失败: {e}")

    try:
        harbor = HarborService()
        results["harbor"] = harbor.test_connection()
    except Exception as e:
        logger.error(f"Harbor 连接测试失败: {e}")

    logger.info(f"[Celery] 连接测试结果: {results}")
    return results
