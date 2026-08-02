# -*- coding: utf-8 -*-
"""
Jenkins Job & Pipeline 批量导入脚本

读取用户独立脚本导出的 JSON 文件目录，通过 git_url 反查 CodeRepository，
自动建立 Application / PipelineTemplate / PipelineTemplateVersion /
ApplicationPipelineConfig 的关联关系，并将 jenkins_job_name 保存为原始 job 全路径，
保证后续同步时不会重命名已有 Jenkins job。

JSON 文件结构（与 docs/jenkinsjob-json.py 导出格式一致）:
{
    "template": {
        "name": "job_full_name",
        "code": "job_full_name",
        "language": "java",
        "language_version": "17",
        "framework": "springboot",
        "description": "...",
        "git_url": "ssh://git@host:port/group/repo.git"
    },
    "version": {
        "version": "1.0.3",
        "content": "pipeline script or // Pipeline from SCM: ...",
        "variables": {},
        "stages": [],
        "stages_content": {}
    }
}

用法:
    # 预检（不写库，输出匹配/未匹配报告）
    python manage.py import_jenkins_jobs --dir ./jenkins_jobs_export --dry-run

    # 正式导入，关联到测试环境
    python manage.py import_jenkins_jobs --dir ./jenkins_jobs_export --environment test

    # 指定默认应用类型和构建分支
    python manage.py import_jenkins_jobs --dir ./jenkins_jobs_export --app-type java --build-branch main
"""
import json
import os
import re
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from release.models import (
    Application,
    ApplicationPipelineConfig,
    CodeRepository,
    PipelineTemplate,
    PipelineTemplateVersion,
)
from utils.models import CommonStatus


# 从语言/框架推导应用类型
LANGUAGE_TO_APP_TYPE = {
    "java": "java",
    "nodejs": "nodejs",
    "node": "nodejs",
    "javascript": "nodejs",
    "typescript": "nodejs",
    "python": "python",
    "go": "go",
    "golang": "go",
    "vue": "vue",
    "react": "react",
}


def normalize_git_url(url: str) -> str:
    """标准化 git url 以便匹配：去除 .git 后缀、统一小写协议头"""
    if not url:
        return ""
    url = url.strip()
    # 去除 .git 后缀
    if url.endswith(".git"):
        url = url[:-4]
    return url


def match_code_repository(git_url: str):
    """
    通过 git_url 匹配 CodeRepository。

    匹配策略（按优先级）:
      1. CodeRepository.git_http_url 完全匹配（标准化后）
      2. CodeRepository.git_url 完全匹配（标准化后）
      3. 去除协议头后路径部分匹配（应对端口/协议差异）

    返回: CodeRepository 实例 或 None
    """
    if not git_url:
        return None

    normalized = normalize_git_url(git_url)
    if not normalized:
        return None

    # 策略1: git_http_url 完全匹配
    for repo in CodeRepository.objects.filter(
        is_deleted=False, git_http_url__isnull=False
    ).exclude(git_http_url=""):
        if normalize_git_url(repo.git_http_url) == normalized:
            return repo

    # 策略2: git_url (SSH) 完全匹配
    for repo in CodeRepository.objects.filter(
        is_deleted=False, git_url__isnull=False
    ).exclude(git_url=""):
        if normalize_git_url(repo.git_url) == normalized:
            return repo

    # 策略3: 路径部分匹配（去除协议和 host 后的 path 部分）
    # 例: ssh://git@host:port/a/b  vs  http://other-host/a/b  -> 匹配 /a/b
    path_match = re.search(r'://[^/]+(/.+)$', normalized)
    if path_match:
        target_path = path_match.group(1).rstrip('/')
        for repo in CodeRepository.objects.filter(is_deleted=False):
            for field in ('git_http_url', 'git_url'):
                val = getattr(repo, field, None)
                if not val:
                    continue
                m = re.search(r'://[^/]+(/.+)$', normalize_git_url(val))
                if m and m.group(1).rstrip('/') == target_path:
                    return repo

    return None


def load_json_file(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


class Command(BaseCommand):
    help = "从导出的 Jenkins job JSON 文件批量导入应用和流水线，自动匹配 CodeRepository 建立关联"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dir",
            default="./jenkins_jobs_export",
            help="JSON 文件所在目录（默认 ./jenkins_jobs_export）",
        )
        parser.add_argument(
            "--environment",
            default="test",
            choices=["dev", "test", "staging", "production"],
            help="关联的环境（默认 test 测试环境）",
        )
        parser.add_argument(
            "--app-type",
            default=None,
            help="应用类型（java/nodejs/python/go/vue/react），默认根据 language 推导",
        )
        parser.add_argument(
            "--build-branch",
            default="main",
            help="默认构建分支（默认 main）",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="预检模式：只输出匹配结果报告，不写入数据库",
        )
        parser.add_argument(
            "--skip-existing",
            action="store_true",
            default=True,
            help="已存在的 Application 跳过，不重复创建（默认启用）",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="强制覆盖已存在的数据（慎用，会先删除再重建）",
        )

    def handle(self, *args, **options):
        json_dir = options["dir"]
        environment = options["environment"]
        default_app_type = options["app_type"]
        build_branch = options["build_branch"]
        dry_run = options["dry_run"]
        skip_existing = options["skip_existing"]
        force = options["force"]

        if not os.path.isdir(json_dir):
            self.stderr.write(self.style.ERROR(f"目录不存在: {json_dir}"))
            return

        json_files = sorted(Path(json_dir).glob("*.json"))
        if not json_files:
            self.stdout.write(self.style.WARNING(f"目录 {json_dir} 下未找到 JSON 文件"))
            return

        self.stdout.write(self.style.SUCCESS(
            f"找到 {len(json_files)} 个 JSON 文件，环境={environment}，"
            f"dry_run={dry_run}, force={force}"
        ))
        self.stdout.write("-" * 80)

        # 统计
        matched = []      # (file, job_name, repo_id, project_id, module_id)
        unmatched = []    # (file, job_name, git_url)
        skipped = []      # (file, job_name, reason)
        errors = []       # (file, job_name, error)
        imported = []     # (file, job_name, app_id)

        for idx, json_file in enumerate(json_files, 1):
            fname = json_file.name
            self.stdout.write(f"[{idx}/{len(json_files)}] 处理 {fname}")

            try:
                data = load_json_file(str(json_file))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"  读取 JSON 失败: {e}"))
                errors.append((fname, "?", str(e)))
                continue

            template_data = data.get("template", {})
            version_data = data.get("version", {})

            job_name = template_data.get("name") or template_data.get("code")
            if not job_name:
                self.stderr.write(self.style.ERROR("  缺少 template.name/code，跳过"))
                errors.append((fname, "?", "missing name/code"))
                continue

            git_url = template_data.get("git_url", "")

            # 匹配 CodeRepository
            repo = match_code_repository(git_url)
            if not repo:
                self.stdout.write(self.style.WARNING(
                    f"  未匹配到 CodeRepository: job={job_name}, git_url={git_url}"
                ))
                unmatched.append((fname, job_name, git_url))
                continue

            project = repo.project
            module = repo.module
            self.stdout.write(
                f"  匹配成功: repo={repo.name}(id={repo.id}), "
                f"project={project.name if project else 'N/A'}, "
                f"module={module.name if module else 'N/A'}"
            )
            matched.append((fname, job_name, repo.id,
                            project.id if project else None,
                            module.id if module else None))

            if dry_run:
                continue

            # ============ 正式导入 ============
            try:
                with transaction.atomic():
                    # 1. 检查/创建 Application
                    app_qs = Application.objects.filter(
                        project=project,
                        module=module,
                        code=job_name,
                        is_deleted=False,
                    )
                    if app_qs.exists():
                        if skip_existing and not force:
                            self.stdout.write(self.style.WARNING(
                                f"  Application 已存在，跳过: {job_name}"
                            ))
                            skipped.append((fname, job_name, "already exists"))
                            continue
                        if force:
                            # 软删除旧的，重建
                            app_qs.update(is_deleted=True)
                            self.stdout.write(f"  强制覆盖：已软删除旧 Application")

                    # 推导 app_type
                    language = template_data.get("language", "") or ""
                    app_type = default_app_type or LANGUAGE_TO_APP_TYPE.get(
                        language.lower(), "java"
                    )

                    app = Application.objects.create(
                        project=project,
                        module=module,
                        name=job_name,
                        code=job_name,
                        description=template_data.get("description", "")[:256],
                        app_type=app_type,
                        code_repository=repo,
                        git_url=repo.git_url or repo.git_http_url or git_url,
                        gitlab_project_id=repo.gitlab_project_id,
                        build_branch=build_branch,
                        jenkins_sync_status=2,  # 已同步
                        jenkins_sync_time=timezone.now(),
                        jenkins_sync_message="通过导入脚本创建（已存在 Jenkins job）",
                        status=CommonStatus.ENABLED,
                        creator="system_import",
                        modifier="system_import",
                    )

                    # 2. 创建 PipelineTemplate + PipelineTemplateVersion
                    template_code = job_name
                    # 若 template code 已存在，附加后缀避免冲突
                    if PipelineTemplate.objects.filter(
                        code=template_code, is_deleted=False
                    ).exists():
                        template_code = f"{job_name}_{app.id}"

                    template = PipelineTemplate.objects.create(
                        name=job_name,
                        code=template_code,
                        language=template_data.get("language", "java"),
                        language_version=template_data.get("language_version") or "",
                        framework=template_data.get("framework") or "",
                        description=template_data.get("description", ""),
                        is_official=False,
                        status=CommonStatus.ENABLED,
                        creator="system_import",
                        modifier="system_import",
                    )

                    version = PipelineTemplateVersion.objects.create(
                        template=template,
                        version=version_data.get("version", "1.0.0"),
                        content=version_data.get("content", ""),
                        variables=version_data.get("variables", {}) or {},
                        stages=version_data.get("stages", []) or [],
                        stages_content=version_data.get("stages_content", {}) or {},
                        change_log="通过导入脚本从 Jenkins job 创建",
                        is_latest=True,
                        status=CommonStatus.ENABLED,
                        creator="system_import",
                        modifier="system_import",
                    )
                    # 确保同一 template 下其它版本 is_latest=False
                    PipelineTemplateVersion.objects.filter(
                        template=template, is_latest=True
                    ).exclude(pk=version.pk).update(is_latest=False)

                    # 3. 创建 ApplicationPipelineConfig（关联到指定环境）
                    config, created = ApplicationPipelineConfig.objects.get_or_create(
                        application=app,
                        environment=environment,
                        defaults={
                            "template": template,
                            "template_version": version,
                            "is_active": True,
                            "jenkins_sync_status": 2,  # 已同步
                            "jenkins_sync_time": timezone.now(),
                            "jenkins_sync_message": "通过导入脚本创建，job 已存在",
                            "jenkins_job_name": job_name,  # 保留原始 job 全路径
                            "config_dirty": False,
                            "creator": "system_import",
                            "modifier": "system_import",
                        },
                    )
                    if not created:
                        # 配置已存在，更新关联关系和 jenkins_job_name
                        config.template = template
                        config.template_version = version
                        config.jenkins_job_name = job_name
                        config.jenkins_sync_status = 2
                        config.jenkins_sync_time = timezone.now()
                        config.jenkins_sync_message = "通过导入脚本更新，job 已存在"
                        config.config_dirty = False
                        config.save()

                    imported.append((fname, job_name, app.id))
                    self.stdout.write(self.style.SUCCESS(
                        f"  导入成功: app_id={app.id}, template_id={template.id}, "
                        f"config_id={config.id}"
                    ))

            except Exception as e:
                self.stderr.write(self.style.ERROR(f"  导入失败: {e}"))
                import traceback
                traceback.print_exc()
                errors.append((fname, job_name, str(e)))

        # ============ 汇总报告 ============
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("导入汇总报告"))
        self.stdout.write("=" * 80)
        self.stdout.write(f"总文件数: {len(json_files)}")
        self.stdout.write(f"匹配成功: {len(matched)}")
        self.stdout.write(f"未匹配: {len(unmatched)}")
        self.stdout.write(f"跳过(已存在): {len(skipped)}")
        self.stdout.write(f"导入成功: {len(imported)}")
        self.stdout.write(f"错误: {len(errors)}")

        if unmatched:
            self.stdout.write("\n--- 未匹配列表（需人工补关联）---")
            for fname, job_name, git_url in unmatched:
                self.stdout.write(f"  {job_name}  git_url={git_url}  ({fname})")

        if skipped:
            self.stdout.write("\n--- 跳过列表 ---")
            for fname, job_name, reason in skipped:
                self.stdout.write(f"  {job_name}  原因={reason}  ({fname})")

        if errors:
            self.stdout.write("\n--- 错误列表 ---")
            for fname, job_name, err in errors:
                self.stdout.write(f"  {job_name}  错误={err}  ({fname})")

        if dry_run:
            self.stdout.write(self.style.WARNING(
                "\n[DRY-RUN] 未写入数据库。确认无误后去掉 --dry-run 参数正式导入。"
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"\n导入完成: {len(imported)}/{len(matched)} 个匹配的 job 已入库。"
            ))
