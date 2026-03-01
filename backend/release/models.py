# -*- coding: utf-8 -*-
"""
发布管理数据模型
"""
from django.db import models
from utils.models import CoreModel, CommonStatus


class Project(CoreModel):
    """发布项目"""
    name = models.CharField(max_length=64, verbose_name="项目名称")
    code = models.CharField(max_length=32, unique=True, verbose_name="项目编码")
    description = models.CharField(max_length=256, null=True, blank=True, verbose_name="项目描述")
    gitlab_group_id = models.IntegerField(null=True, blank=True, verbose_name="GitLab Group ID")
    status = models.IntegerField(
        choices=CommonStatus.choices,
        default=CommonStatus.ENABLED,
        verbose_name="状态"
    )
    sort = models.IntegerField(default=0, verbose_name="排序")

    class Meta:
        db_table = "release_project"
        verbose_name = "发布项目"
        verbose_name_plural = verbose_name
        ordering = ["-sort", "-create_time"]

    def __str__(self):
        return self.name


class Module(CoreModel):
    """发布模块"""
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE,
        related_name="modules", verbose_name="所属项目"
    )
    name = models.CharField(max_length=64, verbose_name="模块名称")
    code = models.CharField(max_length=32, verbose_name="模块编码")
    description = models.CharField(max_length=256, null=True, blank=True, verbose_name="模块描述")
    gitlab_subgroup_id = models.IntegerField(null=True, blank=True, verbose_name="GitLab Subgroup ID")
    status = models.IntegerField(
        choices=CommonStatus.choices,
        default=CommonStatus.ENABLED,
        verbose_name="状态"
    )
    sort = models.IntegerField(default=0, verbose_name="排序")

    class Meta:
        db_table = "release_module"
        verbose_name = "发布模块"
        verbose_name_plural = verbose_name
        ordering = ["-sort", "-create_time"]
        constraints = [
            models.UniqueConstraint(fields=['project', 'code'], name='uk_project_code')
        ]

    def __str__(self):
        return f"{self.project.name}/{self.name}"


class Application(CoreModel):
    """发布应用"""
    APP_TYPE_CHOICES = [
        ("java", "Java"),
        ("nodejs", "Node.js"),
        ("python", "Python"),
        ("go", "Go"),
        ("vue", "Vue"),
        ("react", "React"),
    ]

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE,
        related_name="applications", verbose_name="所属项目"
    )
    module = models.ForeignKey(
        Module, on_delete=models.CASCADE,
        related_name="applications", verbose_name="所属模块"
    )
    name = models.CharField(max_length=64, verbose_name="应用名称")
    code = models.CharField(max_length=32, verbose_name="应用编码")
    description = models.CharField(max_length=256, null=True, blank=True, verbose_name="应用描述")
    app_type = models.CharField(max_length=16, choices=APP_TYPE_CHOICES, verbose_name="应用类型")
    git_url = models.CharField(max_length=256, null=True, blank=True, verbose_name="Git仓库地址")
    gitlab_project_id = models.IntegerField(null=True, blank=True, verbose_name="GitLab Project ID")
    jenkins_ci_job = models.CharField(max_length=128, null=True, blank=True, verbose_name="Jenkins CI任务")
    jenkins_cd_job = models.CharField(max_length=128, null=True, blank=True, verbose_name="Jenkins CD任务")
    harbor_project = models.CharField(max_length=64, null=True, blank=True, verbose_name="Harbor项目")
    build_branch = models.CharField(max_length=64, default="main", verbose_name="构建分支")
    dockerfile_path = models.CharField(max_length=128, default="./Dockerfile", verbose_name="Dockerfile路径")
    status = models.IntegerField(
        choices=CommonStatus.choices,
        default=CommonStatus.ENABLED,
        verbose_name="状态"
    )
    sort = models.IntegerField(default=0, verbose_name="排序")

    class Meta:
        db_table = "release_application"
        verbose_name = "发布应用"
        verbose_name_plural = verbose_name
        ordering = ["-sort", "-create_time"]
        constraints = [
            models.UniqueConstraint(fields=['module', 'code'], name='uk_module_code')
        ]

    def __str__(self):
        return f"{self.project.name}/{self.module.name}/{self.name}"


class ConfigPackage(CoreModel):
    """配置包"""
    SYNC_STATUS_CHOICES = [
        (0, "待同步"),
        (1, "同步中"),
        (2, "已同步"),
        (3, "同步失败"),
    ]

    app = models.ForeignKey(
        Application, on_delete=models.CASCADE,
        related_name="config_packages", verbose_name="关联应用"
    )
    version = models.CharField(max_length=32, verbose_name="配置包版本")
    file_path = models.CharField(max_length=256, verbose_name="文件路径")
    file_size = models.BigIntegerField(verbose_name="文件大小(字节)")
    checksum = models.CharField(max_length=64, verbose_name="文件校验和")
    sync_status = models.IntegerField(
        choices=SYNC_STATUS_CHOICES,
        default=0,
        verbose_name="同步状态"
    )
    sync_time = models.DateTimeField(null=True, blank=True, verbose_name="同步时间")
    sync_message = models.CharField(max_length=512, null=True, blank=True, verbose_name="同步消息")

    class Meta:
        db_table = "release_config_package"
        verbose_name = "配置包"
        verbose_name_plural = verbose_name
        ordering = ["-create_time"]

    def __str__(self):
        return f"{self.app.name}_v{self.version}"


class SyncLog(CoreModel):
    """同步日志"""
    ACTION_CHOICES = [
        ("create", "创建"),
        ("update", "更新"),
        ("delete", "删除"),
    ]

    SYNC_TYPE_CHOICES = [
        ("harbor", "Harbor"),
        ("jenkins", "Jenkins"),
        ("ansible", "Ansible"),
    ]

    config_package = models.ForeignKey(
        ConfigPackage, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="sync_logs", verbose_name="配置包"
    )
    project = models.ForeignKey(
        Project, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="sync_logs", verbose_name="项目"
    )
    module = models.ForeignKey(
        Module, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="sync_logs", verbose_name="模块"
    )
    app = models.ForeignKey(
        Application, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="sync_logs", verbose_name="应用"
    )
    sync_type = models.CharField(max_length=16, choices=SYNC_TYPE_CHOICES, verbose_name="同步类型")
    resource_name = models.CharField(max_length=128, verbose_name="资源名称")
    action = models.CharField(max_length=16, choices=ACTION_CHOICES, verbose_name="操作")
    status = models.IntegerField(verbose_name="状态: 0-失败, 1-成功")
    message = models.CharField(max_length=1024, null=True, blank=True, verbose_name="日志消息")

    class Meta:
        db_table = "release_sync_log"
        verbose_name = "同步日志"
        verbose_name_plural = verbose_name
        ordering = ["-create_time"]


class Template(CoreModel):
    """发布模板"""
    TEMPLATE_TYPE_CHOICES = [
        ("jenkinsfile", "Jenkinsfile"),
        ("dockerfile", "Dockerfile"),
        ("docker-compose", "Docker Compose"),
    ]

    name = models.CharField(max_length=64, verbose_name="模板名称")
    code = models.CharField(max_length=32, unique=True, verbose_name="模板编码")
    template_type = models.CharField(max_length=16, choices=TEMPLATE_TYPE_CHOICES, verbose_name="模板类型")
    app_type = models.CharField(max_length=16, null=True, blank=True, verbose_name="适用应用类型")
    content = models.TextField(verbose_name="模板内容")
    description = models.CharField(max_length=256, null=True, blank=True, verbose_name="模板描述")
    status = models.IntegerField(
        choices=CommonStatus.choices,
        default=CommonStatus.ENABLED,
        verbose_name="状态"
    )

    class Meta:
        db_table = "release_template"
        verbose_name = "发布模板"
        verbose_name_plural = verbose_name
        ordering = ["-create_time"]

    def __str__(self):
        return self.name
