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

    jenkins = JenkinsService()

    try:
        app.jenkins_sync_status = 1
        app.save(update_fields=['jenkins_sync_status'])

        if force and app.jenkins_ci_job:
            app.jenkins_ci_job = None
            app.jenkins_cd_job = None
            app.save(update_fields=['jenkins_ci_job', 'jenkins_cd_job'])
            logger.info(f"[Celery] 强制重新创建，清除现有 Jenkins Jobs")

        if app.jenkins_ci_job:
            logger.info(f"[Celery] Jenkins Jobs 已存在: {app.jenkins_ci_job}")
            app.jenkins_sync_status = 2
            app.jenkins_sync_time = timezone.now()
            app.jenkins_sync_message = "Jenkins Jobs 已存在"
            app.save(update_fields=['jenkins_sync_status', 'jenkins_sync_time', 'jenkins_sync_message'])
            return {"success": True, "skipped": True, "reason": "jobs_exist"}

        if not app.git_url:
            logger.warning(f"[Celery] 应用没有 Git URL")
            app.jenkins_sync_status = 3
            app.jenkins_sync_message = "应用没有 Git 仓库地址"
            app.save(update_fields=['jenkins_sync_status', 'jenkins_sync_message'])
            return {"success": False, "error": "no_git_url"}

        results = jenkins.create_ci_cd_jobs(
            project_code=app.project.code,
            module_code=app.module.code,
            app_code=app.code,
            git_url=app.git_url,
            branch=app.build_branch
        )

        with transaction.atomic():
            app.jenkins_ci_job = jenkins.get_job_full_name(
                app.project.code, app.module.code, app.code, "ci"
            )
            app.jenkins_cd_job = jenkins.get_job_full_name(
                app.project.code, app.module.code, app.code, "cd"
            )
            app.jenkins_sync_status = 2
            app.jenkins_sync_time = timezone.now()
            app.jenkins_sync_message = "创建成功"
            app.save(update_fields=["jenkins_ci_job", "jenkins_cd_job", "jenkins_sync_status", "jenkins_sync_time", "jenkins_sync_message"])

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
    同步应用的 CI/CD 配置到 Jenkins

    Args:
        app_id: Application ID
    """
    from django.utils import timezone
    from .models import Application, SyncLog
    from .services import JenkinsService, DevOpsException

    logger.info(f"[Celery] 开始同步应用 Jenkins 配置: app_id={app_id}")

    try:
        app = Application.objects.select_related(
            'project', 'module', 'ci_template', 'cd_template'
        ).get(pk=app_id)
    except Application.DoesNotExist:
        logger.error(f"[Celery] 应用不存在: app_id={app_id}")
        return {"success": False, "error": "应用不存在"}

    # 更新状态为"同步中"
    app.jenkins_sync_status = 1
    app.save(update_fields=['jenkins_sync_status'])

    results = {"ci": None, "cd": None}

    try:
        jenkins = JenkinsService()
        folder = f"{app.project.code}/{app.module.code}"

        # 同步 CI Job
        if app.ci_template:
            result = _sync_single_job(
                jenkins=jenkins,
                app=app,
                template=app.ci_template,
                variables=app.ci_variables or {},
                job_type='ci',
                folder=folder
            )
            results["ci"] = result

        # 同步 CD Job
        if app.cd_template:
            result = _sync_single_job(
                jenkins=jenkins,
                app=app,
                template=app.cd_template,
                variables=app.cd_variables or {},
                job_type='cd',
                folder=folder
            )
            results["cd"] = result

        # 更新同步状态
        all_success = all(
            r is None or r.get("success")
            for r in [results["ci"], results["cd"]]
        )

        with transaction.atomic():
            app.jenkins_sync_status = 2 if all_success else 3
            app.jenkins_sync_time = timezone.now()
            app.jenkins_sync_message = "同步成功" if all_success else "部分同步失败"
            app.save(update_fields=['jenkins_sync_status', 'jenkins_sync_time', 'jenkins_sync_message'])

        logger.info(f"[Celery] 应用 Jenkins 配置同步完成: app_id={app_id}, results={results}")
        return {"success": all_success, "results": results}

    except DevOpsException as e:
        logger.error(f"[Celery] Jenkins 配置同步失败: {e.message}")

        app.jenkins_sync_status = 3
        app.jenkins_sync_message = e.message
        app.save(update_fields=['jenkins_sync_status', 'jenkins_sync_message'])

        SyncLog.objects.create(
            app=app,
            project=app.project,
            module=app.module,
            sync_type="jenkins",
            resource_name=f"{app.project.code}/{app.module.code}/{app.code}",
            action="update",
            status=0,
            message=e.message
        )

        raise self.retry(exc=e)

    except Exception as e:
        logger.exception(f"[Celery] Jenkins 配置同步异常: {e}")

        app.jenkins_sync_status = 3
        app.jenkins_sync_message = str(e)[:512]
        app.save(update_fields=['jenkins_sync_status', 'jenkins_sync_message'])

        return {"success": False, "error": str(e)}


def _sync_single_job(jenkins, app, template, variables, job_type, folder):
    """同步单个 Job (CI 或 CD)"""
    from .models import SyncLog

    # 获取最新版本
    latest_version = template.latest_version
    if not latest_version:
        return {"success": False, "error": "模板没有可用版本"}

    # 合并变量
    content = latest_version.content
    template_variables = latest_version.variables or {}

    # 先使用模板默认变量
    final_variables = {}
    if template_variables and isinstance(template_variables, dict):
        for var in template_variables.get('variables', []):
            var_name = var.get('name')
            if var_name:
                final_variables[var_name] = var.get('default', '')

    # 用户变量覆盖
    final_variables.update(variables)

    # 替换变量
    for key, value in final_variables.items():
        content = content.replace(f'${{{key}}}', str(value))

    # Job 名称
    job_name = f"{app.code}-{job_type}"

    # 同步到 Jenkins
    success = jenkins.update_job_config(
        name=job_name,
        folder=folder,
        jenkinsfile_content=content,
        git_url=app.git_url,
        branch=app.build_branch,
        description=f"{job_type.upper()} for {app.project.name}/{app.module.name}/{app.name}"
    )

    if success:
        # 更新 Job 名称
        if job_type == 'ci':
            app.jenkins_ci_job = f"{folder}/{job_name}"
        else:
            app.jenkins_cd_job = f"{folder}/{job_name}"

        # 记录日志
        SyncLog.objects.create(
            app=app,
            project=app.project,
            module=app.module,
            sync_type="jenkins",
            resource_name=f"{folder}/{job_name}",
            action="update",
            status=1,
            message=f"同步 {job_type.upper()} 配置成功: {template.name} v{latest_version.version}"
        )

        return {"success": True, "job_name": f"{folder}/{job_name}"}
    else:
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
            'application__ci_template'
        ).get(pk=release_id)
    except ReleaseRecord.DoesNotExist:
        logger.error(f"[Celery] 发布记录不存在: release_id={release_id}")
        return {"success": False, "error": "发布记录不存在"}

    application = release.application

    try:
        # 优先查找环境的 CI 配置
        from .models import ApplicationPipelineConfig
        pipeline_config = ApplicationPipelineConfig.objects.filter(
            application=application,
            config_type='ci',
            environment=release.environment,
            is_active=True
        ).first()

        # 确定使用的 Jenkins Job
        jenkins_job_name = None
        if pipeline_config and pipeline_config.jenkins_job_name:
            # 使用环境特定的 Job
            jenkins_job_name = pipeline_config.jenkins_job_name
        elif application.ci_template and application.jenkins_ci_job:
            # 使用应用关联的全局 CI Job
            jenkins_job_name = application.jenkins_ci_job
            logger.info(f"[Celery] 使用应用全局 CI Job: {jenkins_job_name}")

        if not jenkins_job_name:
            release.status = 'build_failed'
            release.status_message = f"未找到 {release.environment} 环境的 CI 配置，请先同步 Jenkins 配置"
            release.save(update_fields=['status', 'status_message'])
            return {"success": False, "error": "未找到 CI 配置"}

        jenkins = JenkinsService()

        # 检查必要参数
        if not application.project or not application.project.code:
            release.status = 'build_failed'
            release.status_message = "应用所属项目信息不完整，无法触发构建"
            release.save(update_fields=['status', 'status_message'])
            return {"success": False, "error": "应用所属项目信息不完整"}

        if not application.module or not application.module.code:
            release.status = 'build_failed'
            release.status_message = "应用所属模块信息不完整，无法触发构建"
            release.save(update_fields=['status', 'status_message'])
            return {"success": False, "error": "应用所属模块信息不完整"}

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

        # 构建参数 - 完整的 Jenkins Job 参数
        parameters = {
            'PROJECT': application.project.code,
            'MODULE': application.module.code,
            'APP': application.code,
            'BRANCH': release.branch,
            'VERSION': release.version or '',
            'ENVIRONMENT': release.environment,
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
