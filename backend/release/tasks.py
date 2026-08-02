# -*- coding: utf-8 -*-
"""
发布管理 Celery 异步任务
"""
import logging
from celery import shared_task
from django.db import transaction

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def create_gitlab_resources(self, app_id: int, force: bool = False):
    """
    创建 GitLab 资源的异步任务

    Args:
        app_id: 应用 ID
        force: 是否强制重新创建
    """
    from django.utils import timezone
    from .models import Application, SyncLog
    from .services import GitLabService, DevOpsException

    logger.info(f"[Celery] 开始创建 GitLab 资源: app_id={app_id}, force={force}")

    try:
        app = Application.objects.select_related("project", "module").get(pk=app_id)
    except Application.DoesNotExist:
        logger.error(f"[Celery] 应用不存在: app_id={app_id}")
        return {"success": False, "error": "应用不存在"}

    gitlab = GitLabService()

    try:
        app.gitlab_sync_status = 1
        app.save(update_fields=['gitlab_sync_status'])

        if force and app.gitlab_project_id:
            app.gitlab_project_id = None
            app.git_url = None
            app.save(update_fields=['gitlab_project_id', 'git_url'])
            logger.info(f"[Celery] 强制重新创建，清除现有 GitLab Project")

        if app.gitlab_project_id:
            logger.info(f"[Celery] GitLab Project 已存在: {app.gitlab_project_id}")
            app.gitlab_sync_status = 2
            app.gitlab_sync_time = timezone.now()
            app.gitlab_sync_message = "GitLab Project 已存在"
            app.save(update_fields=['gitlab_sync_status', 'gitlab_sync_time', 'gitlab_sync_message'])
            return {"success": True, "skipped": True, "reason": "project_exists"}

        subgroup_id = app.module.gitlab_subgroup_id
        if not subgroup_id:
            logger.warning(f"[Celery] 模块没有 GitLab Subgroup ID")
            app.gitlab_sync_status = 3
            app.gitlab_sync_message = "模块没有 GitLab Subgroup ID"
            app.save(update_fields=['gitlab_sync_status', 'gitlab_sync_message'])
            return {"success": False, "error": "no_subgroup"}

        project = gitlab.create_project(
            name=app.name,
            path=app.code,
            namespace_id=subgroup_id,
            description=app.description
        )

        with transaction.atomic():
            app.gitlab_project_id = project["id"]
            app.git_url = project.get("ssh_url_to_repo") or project.get("http_url_to_repo")
            app.gitlab_sync_status = 2
            app.gitlab_sync_time = timezone.now()
            app.gitlab_sync_message = "创建成功"
            app.save(update_fields=["gitlab_project_id", "git_url", "gitlab_sync_status", "gitlab_sync_time", "gitlab_sync_message"])

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

        app.gitlab_sync_status = 3
        app.gitlab_sync_message = e.message
        app.save(update_fields=['gitlab_sync_status', 'gitlab_sync_message'])

        SyncLog.objects.create(
            app_id=app_id,
            sync_type="gitlab",
            resource_name=app.code,
            action="create",
            status=0,
            message=e.message
        )

        raise self.retry(exc=e)
    except Exception as e:
        logger.exception(f"[Celery] GitLab 资源创建异常: {e}")
        app.gitlab_sync_status = 3
        app.gitlab_sync_message = str(e)[:512]
        app.save(update_fields=['gitlab_sync_status', 'gitlab_sync_message'])
        return {"success": False, "error": str(e)}


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def create_jenkins_resources(self, app_id: int, force: bool = False):
    """
    创建 Jenkins 资源的异步任务

    Args:
        app_id: 应用 ID
        force: 是否强制重新创建
    """
    from django.utils import timezone
    from .models import Application, SyncLog
    from .services import JenkinsService, DevOpsException

    logger.info(f"[Celery] 开始创建 Jenkins 资源: app_id={app_id}, force={force}")

    try:
        app = Application.objects.select_related("project", "module").get(pk=app_id)
    except Application.DoesNotExist:
        logger.error(f"[Celery] 应用不存在: app_id={app_id}")
        return {"success": False, "error": "应用不存在"}

    from .models import ApplicationPipelineConfig

    jenkins = JenkinsService()

    try:
        app.jenkins_sync_status = 1
        app.save(update_fields=['jenkins_sync_status'])

        if not app.git_url:
            logger.warning(f"[Celery] 应用没有 Git URL")
            app.jenkins_sync_status = 3
            app.jenkins_sync_message = "应用没有 Git 仓库地址"
            app.save(update_fields=['jenkins_sync_status', 'jenkins_sync_message'])
            return {"success": False, "error": "no_git_url"}

        module_code = app.module.code if app.module else app.code
        configs = ApplicationPipelineConfig.objects.filter(
            application=app, is_deleted=False
        )

        created_jobs = []
        for config in configs:
            # 已导入旧 job（通过 import_jenkins_jobs 脚本创建）已有 jenkins_job_name，
            # 跳过创建，保持原始 job 名不变，避免在 Jenkins 上创建重复 job
            if config.jenkins_job_name:
                logger.info(
                    f"[Celery] 跳过已导入 job 的创建: config_id={config.id}, "
                    f"jenkins_job_name={config.jenkins_job_name}"
                )
                created_jobs.append(config.jenkins_job_name)
                continue
            env_code = config.environment
            success = jenkins.create_pipeline_job_with_folder(
                project_code=app.project.code,
                module_code=module_code,
                app_code=app.code,
                environment_code=env_code,
                git_url=app.git_url,
                branch=app.build_branch
            )
            if success:
                job_name = jenkins.get_job_full_name(
                    app.project.code, module_code, app.code, env_code
                )
                ApplicationPipelineConfig.objects.filter(pk=config.pk).update(
                    jenkins_job_name=job_name
                )
                created_jobs.append(job_name)

        all_success = len(created_jobs) >= configs.count() if configs.exists() else False

        with transaction.atomic():
            app.jenkins_sync_status = 2 if all_success else 3
            app.jenkins_sync_time = timezone.now()
            app.jenkins_sync_message = "创建成功" if all_success else "部分创建失败"
            app.save(update_fields=["jenkins_sync_status", "jenkins_sync_time", "jenkins_sync_message"])

        SyncLog.objects.create(
            app=app,
            project=app.project,
            module=app.module,
            sync_type="jenkins",
            resource_name=", ".join(created_jobs) if created_jobs else app.code,
            action="create",
            status=1 if all_success else 0,
            message=f"创建 Jenkins Jobs 成功: {len(created_jobs)}/{configs.count()}"
        )

        logger.info(f"[Celery] Jenkins Jobs 创建成功: {created_jobs}")

        if configs.exists():
            try:
                sync_application_jenkins.delay(app.id)
            except Exception as e:
                logger.exception(f"[Celery] 应用 Pipeline 同步任务提交失败: {e}")

        return {"success": all_success, "jobs": created_jobs}

    except DevOpsException as e:
        logger.error(f"[Celery] Jenkins 资源创建失败: {e.message}")

        app.jenkins_sync_status = 3
        app.jenkins_sync_message = e.message
        app.save(update_fields=['jenkins_sync_status', 'jenkins_sync_message'])

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
        app.jenkins_sync_status = 3
        app.jenkins_sync_message = str(e)[:512]
        app.save(update_fields=['jenkins_sync_status', 'jenkins_sync_message'])
        return {"success": False, "error": str(e)}


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def create_harbor_resources(self, app_id: int, force: bool = False):
    """
    创建 Harbor 资源的异步任务

    Args:
        app_id: 应用 ID
        force: 是否强制重新创建
    """
    from django.utils import timezone
    from .models import Application, SyncLog
    from .services import HarborService, DevOpsException

    logger.info(f"[Celery] 开始创建 Harbor 资源: app_id={app_id}, force={force}")

    try:
        app = Application.objects.select_related("project", "module").get(pk=app_id)
    except Application.DoesNotExist:
        logger.error(f"[Celery] 应用不存在: app_id={app_id}")
        return {"success": False, "error": "应用不存在"}

    harbor = HarborService()

    try:
        app.harbor_sync_status = 1
        app.save(update_fields=['harbor_sync_status'])

        if force and app.harbor_project:
            app.harbor_project = None
            app.save(update_fields=['harbor_project'])
            logger.info(f"[Celery] 强制重新创建，清除现有 Harbor Project")

        if app.harbor_project:
            logger.info(f"[Celery] Harbor Project 已存在: {app.harbor_project}")
            app.harbor_sync_status = 2
            app.harbor_sync_time = timezone.now()
            app.harbor_sync_message = "Harbor Project 已存在"
            app.save(update_fields=['harbor_sync_status', 'harbor_sync_time', 'harbor_sync_message'])
            return {"success": True, "skipped": True, "reason": "project_exists"}

        project_name = f"{app.project.code}-{app.module.code}"
        project = harbor.create_project(project_name)

        with transaction.atomic():
            app.harbor_project = project_name
            app.harbor_sync_status = 2
            app.harbor_sync_time = timezone.now()
            app.harbor_sync_message = "创建成功"
            app.save(update_fields=["harbor_project", "harbor_sync_status", "harbor_sync_time", "harbor_sync_message"])

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

        app.harbor_sync_status = 3
        app.harbor_sync_message = e.message
        app.save(update_fields=['harbor_sync_status', 'harbor_sync_message'])

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
        app.harbor_sync_status = 3
        app.harbor_sync_message = str(e)[:512]
        app.save(update_fields=['harbor_sync_status', 'harbor_sync_message'])
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


# ============================================================
# Jenkins 配置同步任务
# ============================================================

@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def sync_application_jenkins(self, app_id: int):
    """
    同步应用的 Pipeline 配置到 Jenkins

    Args:
        app_id: Application ID
    """
    from django.utils import timezone
    from .models import Application, ApplicationPipelineConfig, SyncLog
    from .services import JenkinsService, DevOpsException

    logger.info(f"[Celery] 开始同步应用 Pipeline 配置: app_id={app_id}")

    try:
        app = Application.objects.select_related('project', 'module').get(pk=app_id)
    except Application.DoesNotExist:
        logger.error(f"[Celery] 应用不存在: app_id={app_id}")
        return {"success": False, "error": "应用不存在"}

    configs = ApplicationPipelineConfig.objects.filter(
        application=app, is_active=True, is_deleted=False,
        template__isnull=False
    ).select_related('template', 'template_version', 'application')

    if not configs.exists():
        # 无启用流水线配置，应用级状态由聚合得出（应为“未配置”）
        app.refresh_jenkins_sync_status()
        return {"success": True, "results": [], "message": "无启用的流水线配置，无需同步"}

    module_code = app.module.code if app.module else app.code
    folder = f"{app.project.code}/{module_code}/{app.code}"

    # 批量开始：各环境先置为同步中，应用级状态由聚合逻辑派生
    ApplicationPipelineConfig.objects.filter(
        pk__in=list(configs.values_list('id', flat=True))
    ).update(jenkins_sync_status=1)
    app.refresh_jenkins_sync_status()

    results = []

    try:
        jenkins = JenkinsService()

        for config in configs:
            result = _sync_pipeline_config(jenkins, app, config, folder)
            results.append(result)

        # 每条 config 保存时已触发聚合；这里再确保最终状态正确
        app.refresh_jenkins_sync_status()
        all_success = all(r.get("success") for r in results)
        logger.info(f"[Celery] 应用 Pipeline 配置同步完成: app_id={app_id}, results={results}")
        return {"success": all_success, "results": results}

    except DevOpsException as e:
        logger.error(f"[Celery] Pipeline 配置同步失败: {e.message}")
        SyncLog.objects.create(
            app=app, project=app.project, module=app.module,
            sync_type="jenkins",
            resource_name=folder,
            action="update", status=0, message=e.message
        )
        app.refresh_jenkins_sync_status()
        raise self.retry(exc=e)
    except Exception as e:
        logger.exception(f"[Celery] Pipeline 配置同步异常: {e}")
        app.refresh_jenkins_sync_status()
        return {"success": False, "error": str(e)}


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def sync_jenkins_config(self, config_id):
    """同步单个 Pipeline 配置到 Jenkins（独立任务，由 generate_and_sync / sync_to_jenkins 触发）"""
    from django.utils import timezone
    from .models import ApplicationPipelineConfig, SyncLog
    from .services import JenkinsService, DevOpsException
    from .pipeline_utils import get_template_content, build_pipeline_variables

    config = ApplicationPipelineConfig.objects.select_related(
        'application', 'application__project', 'application__module',
        'template', 'template_version'
    ).get(pk=config_id)

    app = config.application

    try:
        latest_version = config.get_config_version()
        if latest_version and latest_version.content:
            content = latest_version.content
        else:
            template_content, template_variables = get_template_content(config)
            if not template_content:
                raise ValueError(f"配置 {config_id} 没有关联模板或模板版本")
            variables = build_pipeline_variables(app, config, template_variables)
            content = template_content
            for key, value in variables.items():
                content = content.replace(f'${{{key}}}', str(value))

        jenkins = JenkinsService()

        # 区分已导入旧 job 和新建 job：
        # - 旧 job（通过导入脚本创建）已有 jenkins_job_name，按原始路径同步，保持原名不变
        # - 新建 job 用系统命名规则 folder=project.code/module.code/app.code, name=env_code
        if config.jenkins_job_name:
            parts = config.jenkins_job_name.split('/')
            job_name = parts[-1]
            folder = '/'.join(parts[:-1]) if len(parts) > 1 else None
            logger.info(
                f"[Celery] 已导入旧 job，按原始路径同步: "
                f"jenkins_job_name={config.jenkins_job_name}, folder={folder}, name={job_name}"
            )
        else:
            module_code = app.module.code if app.module else app.code
            folder = f"{app.project.code}/{module_code}/{app.code}"
            job_name = config.environment

        env_code = config.environment
        module_name = app.module.name if app.module else app.name

        success = jenkins.update_job_config(
            name=job_name,
            folder=folder,
            jenkinsfile_content=content,
            git_url=app.git_url,
            branch=app.build_branch,
            description=f"Pipeline for {app.project.name}/{module_name}/{app.name}/{env_code}"
        )

        if success:
            full_job_name = f"{folder}/{job_name}" if folder else job_name
            config.jenkins_job_name = full_job_name
            config.jenkins_sync_status = 2
            config.jenkins_sync_time = timezone.now()
            config.jenkins_sync_message = "同步成功"
            config.config_dirty = False
            config.save()
            return {"success": True, "job_name": full_job_name}
        else:
            ApplicationPipelineConfig.objects.filter(pk=config.pk).update(
                jenkins_sync_status=3,
                jenkins_sync_message="更新 Jenkins Job 失败"
            )
            return {"success": False, "error": "更新 Jenkins Job 失败"}
    except DevOpsException as e:
        logger.error(f"[Celery] Pipeline 同步失败: config_id={config_id}, error={e.message}")
        config.jenkins_sync_status = 3
        config.jenkins_sync_message = e.message
        config.save()
        raise self.retry(exc=e)
    except Exception as e:
        logger.exception(f"[Celery] Pipeline 同步异常: config_id={config_id}")
        config.jenkins_sync_status = 3
        config.jenkins_sync_message = str(e)[:512]
        config.save()
        return {"success": False, "error": str(e)}


def _sync_pipeline_config(jenkins, app, config, folder):
    """同步单个 Pipeline 配置到 Jenkins（被 sync_application_jenkins 调用）"""
    from django.utils import timezone
    from .models import SyncLog, ApplicationPipelineConfig, ApplicationPipelineVersion
    from .pipeline_utils import get_template_content, build_pipeline_variables

    latest_version = ApplicationPipelineVersion.objects.filter(config=config).order_by('-version').first()
    if latest_version and latest_version.content:
        content = latest_version.content
    else:
        template_content, template_variables = get_template_content(config)
        if not template_content:
            return {"success": False, "error": f"配置 {config.id} 没有关联模板或模板版本"}
        variables = build_pipeline_variables(app, config, template_variables)
        content = template_content
        for key, value in variables.items():
            content = content.replace(f'${{{key}}}', str(value))

    env_code = config.environment
    module_name = app.module.name if app.module else app.name

    # 区分已导入旧 job 和新建 job：
    # - 旧 job（通过导入脚本创建）已有 jenkins_job_name，按原始路径同步
    # - 新建 job 用调用方传入的 folder + env_code 作为 name
    if config.jenkins_job_name:
        parts = config.jenkins_job_name.split('/')
        job_name = parts[-1]
        job_folder = '/'.join(parts[:-1]) if len(parts) > 1 else None
        logger.info(
            f"[Celery] 已导入旧 job，按原始路径同步: "
            f"jenkins_job_name={config.jenkins_job_name}, folder={job_folder}, name={job_name}"
        )
    else:
        job_name = env_code
        job_folder = folder

    success = jenkins.update_job_config(
        name=job_name,
        folder=job_folder,
        jenkinsfile_content=content,
        git_url=app.git_url,
        branch=app.build_branch,
        description=f"Pipeline for {app.project.name}/{module_name}/{app.name}/{env_code}"
    )

    if success:
        full_job_name = f"{job_folder}/{job_name}" if job_folder else job_name
        config.jenkins_job_name = full_job_name
        config.jenkins_sync_status = 2
        config.jenkins_sync_time = timezone.now()
        config.jenkins_sync_message = "同步成功"
        config.config_dirty = False
        config.save()
        SyncLog.objects.create(
            app=app, project=app.project, module=app.module,
            sync_type="jenkins",
            resource_name=full_job_name,
            action="update", status=1,
            message=f"同步 Pipeline 配置成功 ({env_code})"
        )
        return {"success": True, "job_name": full_job_name}
    else:
        config.jenkins_sync_status = 3
        config.jenkins_sync_message = "更新 Jenkins Job 失败"
        config.save()
        return {"success": False, "error": "更新 Jenkins Job 失败"}


# ============================================================
# 发布构建任务
# ============================================================

@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def trigger_jenkins_build(self, release_id: int):
    """
    触发 Jenkins 构建

    Args:
        release_id: 发布记录 ID
    """
    from django.utils import timezone
    from .models import ReleaseRecord, SyncLog
    from .services import JenkinsService

    logger.info(f"[Celery] 开始触发 Jenkins 构建: release_id={release_id}")

    try:
        release = ReleaseRecord.objects.select_related(
            'application', 'application__project', 'application__module',
            'application__code_repository'
        ).get(pk=release_id)
    except ReleaseRecord.DoesNotExist:
        logger.error(f"[Celery] 发布记录不存在: release_id={release_id}")
        return {"success": False, "error": "发布记录不存在"}

    application = release.application

    try:
        from .models import ApplicationPipelineConfig
        pipeline_config = ApplicationPipelineConfig.objects.filter(
            application=application,
            environment=release.environment,
            is_active=True
        ).first()

        jenkins_job_name = None
        if pipeline_config and pipeline_config.jenkins_job_name:
            jenkins_job_name = pipeline_config.jenkins_job_name

        if not jenkins_job_name:
            release.status = 'build_failed'
            release.status_message = f"未找到 {release.environment} 环境的 Pipeline 配置，请先同步 Jenkins 配置"
            release.save(update_fields=['status', 'status_message'])
            return {"success": False, "error": "未找到 Pipeline 配置"}

        jenkins = JenkinsService()

        # 检查必要参数
        if not application.project or not application.project.code:
            release.status = 'build_failed'
            release.status_message = "应用所属项目信息不完整，无法触发构建"
            release.save(update_fields=['status', 'status_message'])
            return {"success": False, "error": "应用所属项目信息不完整"}

        # 处理 module 为空的情况
        module_code = application.module.code if application.module else application.code

        if not application.code:
            release.status = 'build_failed'
            release.status_message = "应用编码不存在，无法触发构建"
            release.save(update_fields=['status', 'status_message'])
            return {"success": False, "error": "应用编码不存在"}

        if not release.branch:
            release.status = 'build_failed'
            release.status_message = "发布分支不能为空"
            release.save(update_fields=['status', 'status_message'])
            return {"success": False, "error": "发布分支不能为空"}

        if not release.environment:
            release.status = 'build_failed'
            release.status_message = "发布环境不能为空"
            release.save(update_fields=['status', 'status_message'])
            return {"success": False, "error": "发布环境不能为空"}

        # 获取代码仓库信息
        # 构建配置从 Application 获取：code_subpath, build_command, package_name
        code_repo = None
        git_url = ''
        code_subpath = application.code_subpath or ''
        build_command = application.build_command or ''
        package_name = ''

        if application.code_repository:
            code_repo = application.code_repository
            git_url = code_repo.git_url or ''
            logger.info(f"[Celery] 使用代码仓库: name={code_repo.name}, git_url={git_url}")
        elif application.git_url:
            # 兼容旧数据：使用应用原有的 git_url
            git_url = application.git_url or ''
            logger.info(f"[Celery] 使用应用原有字段: git_url={git_url}")

        # 检查 Git URL
        if not git_url:
            release.status = 'build_failed'
            release.status_message = "代码仓库地址为空，请先关联代码仓库或配置 Git 仓库地址"
            release.save(update_fields=['status', 'status_message'])
            return {"success": False, "error": "代码仓库地址为空"}

        # 构建参数 - 完整的 Jenkins Job 参数
        parameters = {
            'PROJECT': application.project.code,
            'MODULE': module_code,
            'APP': application.code,
            'BRANCH': release.branch,
            'VERSION': release.version or '',
            'ENVIRONMENT': release.environment,
            'GIT_REPO': git_url,
            'CODE_SUBPATH': code_subpath,
            'BUILD_COMMAND': build_command,
            'PACKAGE_NAME': package_name,
        }

        logger.info(f"[Celery] 构建参数: {parameters}")

        # 解析 Job 名称和 Folder
        parts = jenkins_job_name.split('/')
        job_name = parts[-1]
        folder = '/'.join(parts[:-1]) if len(parts) > 1 else None

        logger.info(f"[Celery] 解析 Jenkins Job: jenkins_job_name={jenkins_job_name}, job_name={job_name}, folder={folder}")

        # 检查 Job 是否存在
        if not jenkins.job_exists(job_name, folder):
            logger.error(f"[Celery] Jenkins Job 不存在: {job_name}, folder={folder}")
            release.status = 'build_failed'
            release.status_message = f"Jenkins Job 不存在: {jenkins_job_name}"
            release.save(update_fields=['status', 'status_message'])
            return {"success": False, "error": "Jenkins Job 不存在"}

        # 触发构建
        build_info = jenkins.build_job(
            name=job_name,
            folder=folder,
            parameters=parameters
        )

        logger.info(f"[Celery] build_job 返回: {build_info}")

        if build_info:
            # 更新发布记录
            release.jenkins_job_name = jenkins_job_name
            release.jenkins_build_number = build_info['number']
            release.jenkins_build_url = build_info['url']
            release.status = 'building'
            release.save(update_fields=[
                'jenkins_job_name', 'jenkins_build_number',
                'jenkins_build_url', 'status'
            ])

            # 记录日志
            SyncLog.objects.create(
                app=application,
                project=application.project,
                module=application.module,
                sync_type="jenkins",
                resource_name=f"{jenkins_job_name}#{build_info['number']}",
                action="update",
                status=1,
                message=f"触发构建成功: {release.branch} -> {release.environment}"
            )

            # 异步轮询构建状态
            poll_build_status.delay(release_id)

            logger.info(f"[Celery] 构建触发成功: {jenkins_job_name}#{build_info['number']}")
            return {"success": True, "build_number": build_info['number']}

        else:
            release.status = 'build_failed'
            release.status_message = "触发 Jenkins 构建失败"
            release.save(update_fields=['status', 'status_message'])
            return {"success": False, "error": "触发构建失败"}

    except Exception as e:
        logger.exception(f"[Celery] 触发构建异常: {e}")
        release.status = 'build_failed'
        release.status_message = str(e)[:512]
        release.save(update_fields=['status', 'status_message'])
        return {"success": False, "error": str(e)}


@shared_task(bind=True)
def poll_build_status(self, release_id: int):
    """
    轮询构建状态

    Args:
        release_id: 发布记录 ID
    """
    from django.utils import timezone
    from .models import ReleaseRecord
    from .services import JenkinsService

    try:
        release = ReleaseRecord.objects.get(pk=release_id)
    except ReleaseRecord.DoesNotExist:
        return {"success": False, "error": "发布记录不存在"}

    if release.status != 'building':
        logger.info(f"[Celery] 发布状态非 building，跳过轮询: {release.status}")
        return {"success": True, "status": release.status}

    try:
        jenkins = JenkinsService()

        # 解析 Job 名称和 Folder
        job_full_name = release.jenkins_job_name
        parts = job_full_name.split('/')
        job_name = parts[-1]
        folder = '/'.join(parts[:-1]) if len(parts) > 1 else None

        # 获取构建信息
        build_info = jenkins.get_build_info(
            name=job_name,
            build_number=release.jenkins_build_number,
            folder=folder
        )

        if not build_info:
            # 继续轮询
            poll_build_status.apply_async(args=[release_id], countdown=10)
            return {"success": True, "status": "polling"}

        if build_info.get('building'):
            # 构建中，拉取日志并继续轮询
            fetch_build_log.delay(release_id)
            poll_build_status.apply_async(args=[release_id], countdown=10)
            return {"success": True, "status": "building"}

        # 构建完成
        result = build_info.get('result', 'UNKNOWN')
        release.jenkins_build_status = result
        release.jenkins_build_duration = build_info.get('duration', 0)

        if result == 'SUCCESS':
            release.status = 'build_success'
            release.status_message = "构建成功"
        else:
            release.status = 'build_failed'
            release.status_message = f"构建失败: {result}"

        release.save(update_fields=[
            'jenkins_build_status', 'jenkins_build_duration',
            'status', 'status_message'
        ])

        # 拉取最终日志
        fetch_build_log.delay(release_id)

        logger.info(f"[Celery] 构建完成: {job_full_name}#{release.jenkins_build_number} - {result}")
        return {"success": True, "status": release.status, "result": result}

    except Exception as e:
        logger.exception(f"[Celery] 轮询构建状态异常: {e}")
        # 继续轮询
        poll_build_status.apply_async(args=[release_id], countdown=30)
        return {"success": False, "error": str(e)}


@shared_task
def fetch_build_log(release_id: int):
    """
    拉取构建日志

    Args:
        release_id: 发布记录 ID
    """
    from .models import ReleaseRecord, ReleaseBuildLog
    from .services import JenkinsService

    try:
        release = ReleaseRecord.objects.get(pk=release_id)
    except ReleaseRecord.DoesNotExist:
        return {"success": False, "error": "发布记录不存在"}

    if not release.jenkins_job_name or not release.jenkins_build_number:
        return {"success": False, "error": "缺少构建信息"}

    try:
        jenkins = JenkinsService()

        # 解析 Job 名称和 Folder
        job_full_name = release.jenkins_job_name
        parts = job_full_name.split('/')
        job_name = parts[-1]
        folder = '/'.join(parts[:-1]) if len(parts) > 1 else None

        # 获取控制台输出
        log_content = jenkins.get_build_console_output(
            name=job_name,
            build_number=release.jenkins_build_number,
            folder=folder
        )

        if log_content:
            # 更新或创建日志记录
            ReleaseBuildLog.objects.update_or_create(
                release=release,
                log_type='console',
                defaults={'log_content': log_content}
            )
            return {"success": True}

        return {"success": False, "error": "获取日志失败"}

    except Exception as e:
        logger.exception(f"[Celery] 拉取构建日志异常: {e}")
        return {"success": False, "error": str(e)}


# ============================================================
# 代码仓库同步任务
# ============================================================

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def sync_code_repository_gitlab(self, repo_id: int):
    """
    同步代码仓库到 GitLab

    Args:
        repo_id: 代码仓库 ID
    """
    from django.utils import timezone
    from .models import CodeRepository, SyncLog
    from .services import GitLabService, DevOpsException

    logger.info(f"[Celery] 开始同步代码仓库到 GitLab: repo_id={repo_id}")

    try:
        repo = CodeRepository.objects.select_related('project', 'module').get(pk=repo_id)
    except CodeRepository.DoesNotExist:
        logger.error(f"[Celery] 代码仓库不存在: repo_id={repo_id}")
        return {"success": False, "error": "代码仓库不存在"}

    gitlab = GitLabService()

    try:
        # 严格按照：组 -> 子组 -> 仓库 的逻辑
        # 1. 必须先有项目（Project）的 GitLab Group ID
        # 2. 模块（Module）的 GitLab Subgroup ID 应该是项目 Group 的子组
        # 3. 代码仓库创建在模块的 Subgroup 下（如果有），否则创建在项目的 Group 下
        
        if not repo.project or not repo.project.gitlab_group_id:
            logger.warning(f"[Celery] 代码仓库没有关联项目或项目没有 GitLab Group ID")
            return {"success": False, "error": "请先在项目中配置 GitLab Group ID"}
        
        # 项目 Group ID（必须的根节点）
        project_group_id = repo.project.gitlab_group_id
        logger.info(f"[Celery] 使用项目的 GitLab Group: {project_group_id}")
        
        # 优先使用模块的 Subgroup（子组），作为项目的子组
        if repo.module and repo.module.gitlab_subgroup_id:
            namespace_id = repo.module.gitlab_subgroup_id
            logger.info(f"[Celery] 使用模块的 GitLab Subgroup: {namespace_id}")
        else:
            # 没有模块则使用项目的 Group
            namespace_id = project_group_id
            logger.info(f"[Celery] 使用项目的 GitLab Group: {namespace_id}")

        project = gitlab.create_project(
            name=repo.name,
            path=repo.code,
            namespace_id=namespace_id,
            description=repo.description or '',
            default_branch=repo.default_branch or 'main'
        )

        with transaction.atomic():
            repo.gitlab_project_id = project.get("id")
            if not repo.git_url:
                repo.git_url = project.get("ssh_url_to_repo", "")
            if not repo.git_http_url:
                repo.git_http_url = project.get("http_url_to_repo", "")
            repo.save(update_fields=['gitlab_project_id', 'git_url', 'git_http_url'])

        SyncLog.objects.create(
            project=repo.project,
            module=repo.module,
            app=None,
            sync_type="gitlab",
            resource_name=project.get("path_with_namespace", repo.code),
            action="create",
            status=1,
            message=f"同步代码仓库到 GitLab 成功: {project.get('web_url', '')}"
        )

        logger.info(f"[Celery] 代码仓库同步成功: {project.get('id')}")
        return {"success": True, "gitlab_project_id": project.get("id")}

    except DevOpsException as e:
        logger.error(f"[Celery] 代码仓库同步失败: {e.message}")

        SyncLog.objects.create(
            project=repo.project,
            module=repo.module,
            app=None,
            sync_type="gitlab",
            resource_name=repo.code,
            action="create",
            status=0,
            message=e.message
        )

        raise self.retry(exc=e)
    except Exception as e:
        logger.exception(f"[Celery] 代码仓库同步异常: {e}")
        return {"success": False, "error": str(e)}


@shared_task(bind=True, max_retries=1)
def import_gitlab_projects_batch(self, items: list, username: str):
    """
    批量从 GitLab 导入 Projects（Celery 异步任务）

    Args:
        items: 待导入项列表，每项包含:
            - gitlab_project_id: GitLab Project ID
            - project_id: 可选，业务项目 ID
            - module_id: 可选，业务模块 ID
        username: 创建人用户名
    """
    from django.db import IntegrityError
    from .models import CodeRepository, Project, Module
    from .services import GitLabService, DevOpsException

    logger.info(f"[Celery] 开始批量导入 GitLab Projects: 共 {len(items)} 个, 操作人={username}")

    gitlab = GitLabService()
    success_count = 0
    fail_count = 0
    results = []

    for item in items:
        gitlab_project_id = item.get("gitlab_project_id")
        project_id = item.get("project_id")
        module_id = item.get("module_id")

        logger.info(f"[Celery] 正在导入 GitLab Project {gitlab_project_id} ...")

        # 1. 从 GitLab API 获取项目信息（抛出详细异常）
        try:
            project_info = gitlab.get_project(gitlab_project_id, raise_on_error=True)
        except DevOpsException as e:
            fail_count += 1
            error_msg = f"GitLab API 错误: {e.message}"
            results.append({
                "gitlab_project_id": gitlab_project_id,
                "status": "failed",
                "message": error_msg,
            })
            logger.error(f"[Celery] {error_msg}")
            continue

        if not project_info:
            fail_count += 1
            results.append({
                "gitlab_project_id": gitlab_project_id,
                "status": "failed",
                "message": "GitLab Project 不存在（API 返回空）"
            })
            logger.warning(f"[Celery] GitLab Project {gitlab_project_id} 不存在")
            continue

        project_path = project_info.get("path", "")
        project_name = project_info.get("name", "")

        # 2. 路径截断检查（兼容超长路径）
        if len(project_path) > 256:
            fail_count += 1
            error_msg = f"仓库路径过长: {project_path} ({len(project_path)}字符，最大256)"
            results.append({
                "gitlab_project_id": gitlab_project_id,
                "status": "failed",
                "message": error_msg,
            })
            logger.error(f"[Celery] {error_msg}")
            continue

        # 3. 自动匹配项目和模块
        project_obj = project_id_to_obj(project_id) if project_id else None
        module_obj = module_id_to_obj(module_id) if module_id else None

        if project_obj is None and module_obj is None:
            namespace = project_info.get("namespace", {})
            full_path = namespace.get("full_path", "")
            if full_path:
                path_parts = full_path.split("/")
                if len(path_parts) >= 1:
                    try:
                        project_obj = Project.objects.get(code=path_parts[0], is_deleted=False)
                    except Project.DoesNotExist:
                        pass
                    if project_obj and len(path_parts) >= 2:
                        try:
                            module_obj = Module.objects.get(
                                project=project_obj, code=path_parts[1], is_deleted=False
                            )
                        except Module.DoesNotExist:
                            pass

        # 4. 开始导入
        try:
            # 检查是否已被软删除，是则恢复
            deleted_repo = CodeRepository.objects.filter(
                gitlab_project_id=gitlab_project_id, is_deleted=True
            ).first()
            if deleted_repo:
                deleted_repo.is_deleted = False
                deleted_repo.name = project_name
                deleted_repo.code = project_path
                deleted_repo.git_url = project_info.get("ssh_url_to_repo", "")
                deleted_repo.git_http_url = project_info.get("http_url_to_repo", "")
                deleted_repo.project = project_obj
                deleted_repo.module = module_obj
                deleted_repo.repository_type = 'gitlab'
                try:
                    deleted_repo.save()
                except IntegrityError:
                    fail_count += 1
                    results.append({
                        "gitlab_project_id": gitlab_project_id,
                        "status": "failed",
                        "message": f"恢复失败：项目下已存在同名代码仓库（{project_path}）"
                    })
                    logger.warning(f"[Celery] 恢复失败: {project_path} 已存在")
                    continue
                success_count += 1
                results.append({
                    "gitlab_project_id": gitlab_project_id,
                    "status": "restored",
                    "name": project_name
                })
                logger.info(f"[Celery] 恢复成功: {project_name}")
            else:
                repo = CodeRepository.objects.create(
                    name=project_name,
                    code=project_path,
                    gitlab_project_id=gitlab_project_id,
                    git_url=project_info.get("ssh_url_to_repo", ""),
                    git_http_url=project_info.get("http_url_to_repo", ""),
                    project=project_obj,
                    module=module_obj,
                    repository_type='gitlab',
                    creator=username
                )
                success_count += 1
                results.append({
                    "gitlab_project_id": gitlab_project_id,
                    "status": "success",
                    "id": repo.id,
                    "name": project_name
                })
                logger.info(f"[Celery] 导入成功: {project_name} (id={repo.id})")
        except IntegrityError as e:
            fail_count += 1
            results.append({
                "gitlab_project_id": gitlab_project_id,
                "status": "failed",
                "message": f"数据库约束冲突: {str(e)}"
            })
            logger.error(f"[Celery] 导入失败 (IntegrityError): gitlab_project_id={gitlab_project_id}, error={e}")
        except Exception as e:
            fail_count += 1
            results.append({
                "gitlab_project_id": gitlab_project_id,
                "status": "failed",
                "message": f"导入异常: {type(e).__name__}: {str(e)}"
            })
            logger.exception(f"[Celery] 导入异常: gitlab_project_id={gitlab_project_id}")

    summary = f"批量导入完成: 成功 {success_count} 个, 失败 {fail_count} 个"
    logger.info(f"[Celery] {summary}")
    return {
        "success": True,
        "success_count": success_count,
        "fail_count": fail_count,
        "total": len(items),
        "results": results,
        "message": summary
    }


def project_id_to_obj(project_id):
    """安全获取 Project 对象"""
    if not project_id:
        return None
    from .models import Project
    try:
        return Project.objects.get(id=project_id, is_deleted=False)
    except Project.DoesNotExist:
        return None


def module_id_to_obj(module_id):
    """安全获取 Module 对象"""
    if not module_id:
        return None
    from .models import Module
    try:
        return Module.objects.get(id=module_id, is_deleted=False)
    except Module.DoesNotExist:
        return None
