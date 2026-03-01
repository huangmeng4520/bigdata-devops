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

    JENKINS_SYNC_STATUS_CHOICES = [
        (0, "待同步"),
        (1, "同步中"),
        (2, "已同步"),
        (3, "同步失败"),
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
    # CI/CD 模板关联
    ci_template = models.ForeignKey(
        'PipelineTemplate', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='ci_applications',
        verbose_name="CI 流水线模板"
    )
    cd_template = models.ForeignKey(
        'PipelineTemplate', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='cd_applications',
        verbose_name="CD 流水线模板"
    )
    ci_variables = models.JSONField(default=dict, blank=True, verbose_name="CI 变量配置")
    cd_variables = models.JSONField(default=dict, blank=True, verbose_name="CD 变量配置")
    # Jenkins 同步状态
    jenkins_sync_status = models.IntegerField(
        choices=JENKINS_SYNC_STATUS_CHOICES,
        default=0,
        verbose_name="Jenkins 同步状态"
    )
    jenkins_sync_time = models.DateTimeField(null=True, blank=True, verbose_name="最后同步时间")
    jenkins_sync_message = models.CharField(max_length=512, null=True, blank=True, verbose_name="同步消息")
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
    """发布模板（旧版，保留兼容）"""
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


# ============================================================
# CI/CD 模板系统相关模型
# ============================================================

class PipelineTemplate(CoreModel):
    """流水线模板"""
    TEMPLATE_TYPE_CHOICES = [
        ('ci', 'CI 模板'),
        ('cd', 'CD 模板'),
    ]

    name = models.CharField(max_length=128, verbose_name="模板名称")
    code = models.CharField(max_length=64, unique=True, verbose_name="模板编码")
    template_type = models.CharField(max_length=20, choices=TEMPLATE_TYPE_CHOICES, verbose_name="模板类型")
    language = models.CharField(max_length=32, verbose_name="编程语言")
    language_version = models.CharField(max_length=32, blank=True, null=True, verbose_name="语言版本")
    description = models.TextField(blank=True, null=True, verbose_name="描述")
    framework = models.CharField(max_length=64, blank=True, null=True, verbose_name="框架")
    is_official = models.BooleanField(default=False, verbose_name="官方模板")
    status = models.IntegerField(
        choices=CommonStatus.choices,
        default=CommonStatus.ENABLED,
        verbose_name="状态"
    )

    class Meta:
        db_table = "release_pipeline_template"
        verbose_name = "流水线模板"
        verbose_name_plural = verbose_name
        ordering = ["-create_time"]

    def __str__(self):
        return f"[{self.get_template_type_display()}] {self.name}"

    @property
    def latest_version(self):
        """获取最新版本"""
        return self.versions.filter(is_latest=True, status=CommonStatus.ENABLED).first()


class PipelineTemplateVersion(CoreModel):
    """模板版本"""
    template = models.ForeignKey(
        PipelineTemplate, on_delete=models.CASCADE,
        related_name='versions', verbose_name="所属模板"
    )
    version = models.CharField(max_length=32, verbose_name="版本号")
    content = models.TextField(verbose_name="模板内容 (Jenkinsfile)")
    variables = models.JSONField(default=dict, blank=True, verbose_name="模板变量定义")
    stages = models.JSONField(default=list, blank=True, verbose_name="阶段定义")
    stages_content = models.JSONField(default=dict, blank=True, verbose_name="阶段脚本内容")
    change_log = models.TextField(blank=True, null=True, verbose_name="变更日志")
    is_latest = models.BooleanField(default=False, verbose_name="是否最新版本")
    status = models.IntegerField(
        choices=CommonStatus.choices,
        default=CommonStatus.ENABLED,
        verbose_name="状态"
    )

    class Meta:
        db_table = "release_pipeline_template_version"
        verbose_name = "模板版本"
        verbose_name_plural = verbose_name
        ordering = ["-create_time"]
        constraints = [
            models.UniqueConstraint(fields=['template', 'version'], name='uk_template_version')
        ]

    def __str__(self):
        return f"{self.template.name} v{self.version}"
    
    def auto_increment_version(self):
        """自动递增版本号"""
        import re
        match = re.match(r'(\d+)\.(\d+)\.(\d+)', self.version)
        if match:
            major, minor, patch = map(int, match.groups())
            return f"{major}.{minor}.{patch + 1}"
        return "1.0.1"


class ApplicationPipelineConfig(CoreModel):
    """应用流水线配置"""
    CONFIG_TYPE_CHOICES = [
        ('ci', 'CI 配置'),
        ('cd', 'CD 配置'),
    ]

    ENVIRONMENT_CHOICES = [
        ('dev', '开发环境'),
        ('test', '测试环境'),
        ('staging', '准生产环境'),
        ('production', '生产环境'),
    ]

    SYNC_STATUS_CHOICES = [
        (0, '待同步'),
        (1, '同步中'),
        (2, '已同步'),
        (3, '同步失败'),
    ]

    application = models.ForeignKey(
        Application, on_delete=models.CASCADE,
        related_name='pipeline_configs', verbose_name="所属应用"
    )
    config_type = models.CharField(max_length=20, choices=CONFIG_TYPE_CHOICES, verbose_name="配置类型")
    environment = models.CharField(max_length=32, choices=ENVIRONMENT_CHOICES, verbose_name="环境")
    template = models.ForeignKey(
        PipelineTemplate, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='configs', verbose_name="关联模板"
    )
    template_version = models.ForeignKey(
        PipelineTemplateVersion, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='configs', verbose_name="模板版本"
    )
    custom_content = models.TextField(blank=True, null=True, verbose_name="自定义内容")
    variables = models.JSONField(default=dict, blank=True, verbose_name="变量值")
    stages_config = models.JSONField(default=list, blank=True, verbose_name="阶段配置")
    is_active = models.BooleanField(default=True, verbose_name="是否启用")
    current_version = models.IntegerField(default=0, verbose_name="当前版本号")
    # Jenkins 同步状态
    jenkins_sync_status = models.IntegerField(
        choices=SYNC_STATUS_CHOICES,
        default=0,
        verbose_name="Jenkins 同步状态"
    )
    jenkins_sync_time = models.DateTimeField(null=True, blank=True, verbose_name="最后同步时间")
    jenkins_sync_message = models.CharField(max_length=512, null=True, blank=True, verbose_name="同步消息")
    jenkins_job_name = models.CharField(max_length=256, null=True, blank=True, verbose_name="Jenkins Job 名称")

    class Meta:
        db_table = "release_application_pipeline_config"
        verbose_name = "应用流水线配置"
        verbose_name_plural = verbose_name
        ordering = ["-create_time"]
        constraints = [
            models.UniqueConstraint(
                fields=['application', 'config_type', 'environment'],
                name='uk_app_config_type_env'
            )
        ]

    def __str__(self):
        return f"{self.application.name} - {self.get_config_type_display()} - {self.get_environment_display()}"

    def get_config_version(self):
        """获取最新配置版本"""
        return self.versions.order_by('-version').first()


class ApplicationPipelineVersion(CoreModel):
    """应用配置版本"""
    config = models.ForeignKey(
        ApplicationPipelineConfig, on_delete=models.CASCADE,
        related_name='versions', verbose_name="所属配置"
    )
    version = models.IntegerField(verbose_name="版本号")
    content = models.TextField(verbose_name="生成的 Jenkinsfile")
    variables_snapshot = models.JSONField(default=dict, blank=True, verbose_name="变量快照")
    stages_snapshot = models.JSONField(default=list, blank=True, verbose_name="阶段快照")
    generated_by = models.CharField(max_length=64, verbose_name="生成人")

    class Meta:
        db_table = "release_application_pipeline_version"
        verbose_name = "应用配置版本"
        verbose_name_plural = verbose_name
        ordering = ["-version"]
        constraints = [
            models.UniqueConstraint(fields=['config', 'version'], name='uk_config_version')
        ]

    def __str__(self):
        return f"{self.config.application.name} - v{self.version}"


class EnvironmentStrategy(CoreModel):
    """环境策略"""
    PIPELINE_MODE_CHOICES = [
        ('integrated', 'CI/CD 合并'),
        ('separated', 'CI/CD 分离'),
    ]

    name = models.CharField(max_length=64, verbose_name="策略名称")
    code = models.CharField(max_length=32, unique=True, verbose_name="策略编码")
    environment = models.CharField(max_length=32, verbose_name="环境")
    pipeline_mode = models.CharField(max_length=32, choices=PIPELINE_MODE_CHOICES, verbose_name="流水线模式")
    ci_jenkins = models.CharField(max_length=128, blank=True, null=True, verbose_name="CI Jenkins 标识")
    cd_jenkins = models.CharField(max_length=128, blank=True, null=True, verbose_name="CD Jenkins 标识")
    requires_approval = models.BooleanField(default=False, verbose_name="需要审批")
    auto_deploy = models.BooleanField(default=False, verbose_name="自动部署")
    description = models.TextField(blank=True, null=True, verbose_name="描述")
    is_default = models.BooleanField(default=False, verbose_name="默认策略")
    status = models.IntegerField(
        choices=CommonStatus.choices,
        default=CommonStatus.ENABLED,
        verbose_name="状态"
    )

    class Meta:
        db_table = "release_environment_strategy"
        verbose_name = "环境策略"
        verbose_name_plural = verbose_name
        ordering = ["-create_time"]

    def __str__(self):
        return self.name


class CDConfigExport(CoreModel):
    """CD 配置导出记录"""
    EXPORT_FORMAT_CHOICES = [
        ('jenkinsfile', 'Jenkinsfile'),
        ('json', 'JSON 配置'),
        ('yaml', 'YAML 配置'),
        ('zip', '压缩包'),
    ]

    application = models.ForeignKey(
        Application, on_delete=models.CASCADE,
        related_name='cd_exports', verbose_name="所属应用"
    )
    environment = models.CharField(max_length=32, verbose_name="环境")
    config_version = models.IntegerField(verbose_name="配置版本")
    export_format = models.CharField(max_length=20, choices=EXPORT_FORMAT_CHOICES, verbose_name="导出格式")
    content = models.TextField(verbose_name="导出内容")
    file_path = models.CharField(max_length=512, blank=True, null=True, verbose_name="文件路径")
    exported_by = models.CharField(max_length=64, verbose_name="导出人")
    download_count = models.IntegerField(default=0, verbose_name="下载次数")

    class Meta:
        db_table = "release_cd_config_export"
        verbose_name = "CD配置导出"
        verbose_name_plural = verbose_name
        ordering = ["-create_time"]

    def __str__(self):
        return f"{self.application.name} - {self.environment} - v{self.config_version}"
