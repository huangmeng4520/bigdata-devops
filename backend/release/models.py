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
    gitlab_sync_status = models.CharField(max_length=20, null=True, blank=True, verbose_name="GitLab 同步状态")
    gitlab_sync_message = models.TextField(null=True, blank=True, verbose_name="GitLab 同步消息")
    gitlab_synced_at = models.DateTimeField(null=True, blank=True, verbose_name="GitLab 最后同步时间")
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
    gitlab_sync_status = models.CharField(max_length=20, null=True, blank=True, verbose_name="GitLab 同步状态")
    gitlab_sync_message = models.TextField(null=True, blank=True, verbose_name="GitLab 同步消息")
    gitlab_synced_at = models.DateTimeField(null=True, blank=True, verbose_name="GitLab 最后同步时间")
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


class CodeRepository(models.Model):
    """代码仓库"""

    TYPE_CHOICES = [
        ('gitlab', 'GitLab'),
        ('github', 'GitHub'),
        ('gitee', 'Gitee'),
    ]

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE,
        null=True, blank=True,
        related_name="code_repositories", verbose_name="所属项目"
    )
    module = models.ForeignKey(
        'Module', on_delete=models.SET_NULL,
        null=True, blank=True, related_name="code_repositories", verbose_name="所属模块"
    )
    name = models.CharField(max_length=64, verbose_name="仓库名称")
    code = models.CharField(max_length=32, verbose_name="仓库编码")
    repository_type = models.CharField(max_length=16, choices=TYPE_CHOICES, default='gitlab', verbose_name="仓库类型")
    gitlab_project_id = models.IntegerField(null=True, blank=True, verbose_name="GitLab Project ID")
    git_url = models.CharField(max_length=256, null=True, blank=True, verbose_name="Git SSH 地址")
    git_http_url = models.CharField(max_length=256, null=True, blank=True, verbose_name="Git HTTP 地址")
    default_branch = models.CharField(max_length=64, default='main', verbose_name="默认分支")
    status = models.IntegerField(
        choices=CommonStatus.choices,
        default=CommonStatus.ENABLED,
        verbose_name="状态"
    )
    description = models.CharField(max_length=256, null=True, blank=True, verbose_name="仓库描述")
    creator = models.CharField(max_length=64, null=True, blank=True, verbose_name="创建人")
    modifier = models.CharField(max_length=64, null=True, blank=True, verbose_name="修改人")
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    update_time = models.DateTimeField(auto_now=True, verbose_name="修改时间")
    is_deleted = models.BooleanField(default=False, verbose_name="是否删除")

    class Meta:
        db_table = "release_code_repository"
        verbose_name = "代码仓库"
        verbose_name_plural = verbose_name
        ordering = ["-create_time"]
        constraints = [
            models.UniqueConstraint(fields=['project', 'code'], name='uk_repo_project_code'),
            models.UniqueConstraint(fields=['gitlab_project_id'], name='uk_repo_gitlab_id',
                                   condition=models.Q(gitlab_project_id__isnull=False)),
        ]

    def __str__(self):
        if self.project:
            return f"{self.project.name}/{self.name}"
        return self.name


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
        (4, "待重新同步"),
        (5, "未配置"),
    ]

    GITLAB_SYNC_STATUS_CHOICES = [
        (0, "待同步"),
        (1, "同步中"),
        (2, "已同步"),
        (3, "同步失败"),
    ]

    HARBOR_SYNC_STATUS_CHOICES = [
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
        null=True, blank=True,
        related_name="applications", verbose_name="所属模块"
    )
    name = models.CharField(max_length=64, verbose_name="应用名称")
    code = models.CharField(max_length=32, verbose_name="应用编码")
    description = models.CharField(max_length=256, null=True, blank=True, verbose_name="应用描述")
    app_type = models.CharField(max_length=16, choices=APP_TYPE_CHOICES, verbose_name="应用类型")
    # 代码仓库关联
    code_repository = models.ForeignKey(
        CodeRepository, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='applications', verbose_name="代码仓库"
    )
    code_subpath = models.CharField(max_length=128, null=True, blank=True, verbose_name="代码子目录",
                                   help_text="仓库内的子目录，用于多模块项目构建")
    build_command = models.CharField(max_length=256, null=True, blank=True, verbose_name="编译命令",
                                     help_text="如：mvn clean package 或 npm run build")
    # 兼容旧字段
    git_url = models.CharField(max_length=256, null=True, blank=True, verbose_name="Git仓库地址")
    gitlab_project_id = models.IntegerField(null=True, blank=True, verbose_name="GitLab Project ID")
    harbor_project = models.CharField(max_length=64, null=True, blank=True, verbose_name="Harbor项目")
    build_branch = models.CharField(max_length=64, default="main", verbose_name="构建分支")
    dockerfile_path = models.CharField(max_length=128, default="./Dockerfile", verbose_name="Dockerfile路径")
    # Jenkins 同步状态
    jenkins_sync_status = models.IntegerField(
        choices=JENKINS_SYNC_STATUS_CHOICES,
        default=0,
        verbose_name="Jenkins 同步状态"
    )
    jenkins_sync_time = models.DateTimeField(null=True, blank=True, verbose_name="最后同步时间")
    jenkins_sync_message = models.CharField(max_length=512, null=True, blank=True, verbose_name="同步消息")
    # GitLab 同步状态
    gitlab_sync_status = models.IntegerField(
        choices=GITLAB_SYNC_STATUS_CHOICES,
        default=0,
        verbose_name="GitLab 同步状态"
    )
    gitlab_sync_time = models.DateTimeField(null=True, blank=True, verbose_name="GitLab 最后同步时间")
    gitlab_sync_message = models.CharField(max_length=512, null=True, blank=True, verbose_name="GitLab 同步消息")
    # Harbor 同步状态
    harbor_sync_status = models.IntegerField(
        choices=HARBOR_SYNC_STATUS_CHOICES,
        default=0,
        verbose_name="Harbor 同步状态"
    )
    harbor_sync_time = models.DateTimeField(null=True, blank=True, verbose_name="Harbor 最后同步时间")
    harbor_sync_message = models.CharField(max_length=512, null=True, blank=True, verbose_name="Harbor 同步消息")
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
            models.UniqueConstraint(
                fields=['project', 'module', 'code'], 
                name='uk_project_module_code',
                condition=models.Q(module__isnull=False)
            ),
            models.UniqueConstraint(
                fields=['project', 'code'],
                name='uk_project_code_when_no_module',
                condition=models.Q(module__isnull=True)
            ),
        ]

    def __str__(self):
        return f"{self.project.name}/{self.module.name}/{self.name}"

    def refresh_jenkins_sync_status(self):
        """根据各环境流水线配置状态聚合应用级 Jenkins 同步状态（派生状态）"""
        configs = self.pipeline_configs.filter(is_active=True, is_deleted=False)
        if not configs.exists():
            new_status, message = 5, "未配置流水线"
        else:
            statuses = list(configs.values_list('jenkins_sync_status', flat=True))
            dirty = configs.filter(config_dirty=True).exists()
            if any(s == 1 for s in statuses):
                new_status, message = 1, "同步中"
            elif any(s == 3 for s in statuses):
                new_status, message = 3, "部分环境同步失败"
            elif dirty or any(s == 0 for s in statuses):
                new_status, message = 4, "有环境待重新同步"
            else:
                new_status, message = 2, "全部环境已同步"

            detail = []
            for c in configs:
                if c.jenkins_sync_status == 2 and c.config_dirty:
                    detail.append(f"{c.get_environment_display()}:待重新同步")
                else:
                    detail.append(f"{c.get_environment_display()}:{c.get_jenkins_sync_status_display()}")
            if detail:
                message = f"{message}（{'；'.join(detail)}）"

        if self.jenkins_sync_status != new_status or self.jenkins_sync_message != message:
            self.jenkins_sync_status = new_status
            self.jenkins_sync_message = message
            self.save(update_fields=['jenkins_sync_status', 'jenkins_sync_message'])


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


# ============================================================
# 流水线模板系统相关模型
# ============================================================

class PipelineTemplate(CoreModel):
    """流水线模板"""
    name = models.CharField(max_length=128, verbose_name="模板名称")
    code = models.CharField(max_length=64, unique=True, verbose_name="模板编码")
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
        return self.name

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
    config_dirty = models.BooleanField(default=False, verbose_name="配置已变更待同步")

    class Meta:
        db_table = "release_application_pipeline_config"
        verbose_name = "应用流水线配置"
        verbose_name_plural = verbose_name
        ordering = ["-create_time"]
        constraints = [
            models.UniqueConstraint(
                fields=['application', 'environment'],
                name='uk_app_env'
            )
        ]

    def __str__(self):
        return f"{self.application.name} - {self.get_environment_display()}"

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
    name = models.CharField(max_length=64, verbose_name="策略名称")
    code = models.CharField(max_length=32, unique=True, verbose_name="策略编码")
    environment = models.CharField(max_length=32, verbose_name="环境")
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


# ============================================================
# 发布管理相关模型
# ============================================================

class ReleaseRecord(CoreModel):
    """发布记录"""
    
    STATUS_CHOICES = [
        ('pending', '待发布'),
        ('approval_pending', '待审批'),
        ('approved', '已审批'),
        ('rejected', '已拒绝'),
        ('building', '构建中'),
        ('build_success', '构建成功'),
        ('build_failed', '构建失败'),
        ('deploying', '部署中'),
        ('deployed', '已部署'),
        ('rollback', '已回滚'),
        ('cancelled', '已取消'),
    ]
    
    # 关联应用
    application = models.ForeignKey(
        Application, on_delete=models.CASCADE,
        related_name='releases', verbose_name="所属应用"
    )
    
    # 发布配置
    branch = models.CharField(max_length=128, verbose_name="代码分支")
    environment = models.CharField(
        max_length=32,
        choices=ApplicationPipelineConfig.ENVIRONMENT_CHOICES,
        verbose_name="目标环境"
    )
    version = models.CharField(max_length=64, blank=True, null=True, verbose_name="发布版本")
    
    # 审批信息
    require_approval = models.BooleanField(default=False, verbose_name="需要审批")
    approval_type = models.CharField(max_length=32, blank=True, null=True, verbose_name="审批类型")
    approvers = models.JSONField(default=list, blank=True, verbose_name="审批人列表")
    approval_time = models.DateTimeField(null=True, blank=True, verbose_name="审批时间")
    approval_user = models.CharField(max_length=64, blank=True, null=True, verbose_name="审批人")
    approval_comment = models.TextField(blank=True, null=True, verbose_name="审批意见")
    
    # Jenkins 构建信息
    jenkins_job_name = models.CharField(max_length=256, blank=True, null=True, verbose_name="Jenkins Job 名称")
    jenkins_build_number = models.IntegerField(null=True, blank=True, verbose_name="Jenkins 构建号")
    jenkins_build_url = models.CharField(max_length=512, blank=True, null=True, verbose_name="Jenkins 构建地址")
    jenkins_build_status = models.CharField(max_length=32, blank=True, null=True, verbose_name="Jenkins 构建状态")
    jenkins_build_duration = models.IntegerField(null=True, blank=True, verbose_name="构建耗时(毫秒)")
    
    # 构建产物
    docker_image = models.CharField(max_length=256, blank=True, null=True, verbose_name="Docker 镜像")
    artifact_url = models.CharField(max_length=512, blank=True, null=True, verbose_name="构建产物地址")
    
    # 发布状态
    status = models.CharField(
        max_length=32, choices=STATUS_CHOICES,
        default='pending', verbose_name="发布状态"
    )
    status_message = models.TextField(blank=True, null=True, verbose_name="状态消息")
    
    # AI 分析关联对话
    conversation_id = models.BigIntegerField(
        null=True, blank=True, verbose_name="关联 AI 对话编号",
        db_comment="关联 ai_chat_conversation 的 id"
    )

    # 发布人
    released_by = models.CharField(max_length=64, verbose_name="发布人")
    
    class Meta:
        db_table = "release_record"
        verbose_name = "发布记录"
        verbose_name_plural = verbose_name
        ordering = ["-create_time"]

    def __str__(self):
        return f"{self.application.name} - {self.branch} - {self.get_status_display()}"

    def can_trigger(self):
        """是否可以触发构建"""
        return self.status in ['pending', 'approved', 'build_failed']

    def can_cancel(self):
        """是否可以取消"""
        return self.status in ['pending', 'approval_pending', 'building']

    def can_approve(self):
        """是否可以审批"""
        return self.status == 'approval_pending'


class ReleaseBuildLog(CoreModel):
    """构建日志"""
    
    release = models.ForeignKey(
        ReleaseRecord, on_delete=models.CASCADE,
        related_name='build_logs', verbose_name="关联发布记录"
    )
    
    # 日志内容
    log_content = models.TextField(verbose_name="日志内容")
    log_type = models.CharField(max_length=32, default='console', verbose_name="日志类型")
    
    # 阶段信息
    stage_name = models.CharField(max_length=64, blank=True, null=True, verbose_name="阶段名称")
    stage_status = models.CharField(max_length=32, blank=True, null=True, verbose_name="阶段状态")
    
    class Meta:
        db_table = "release_build_log"
        verbose_name = "构建日志"
        verbose_name_plural = verbose_name
        ordering = ["create_time"]

    def __str__(self):
        return f"{self.release.application.name} - Build #{self.release.jenkins_build_number}"


class ApprovalRule(CoreModel):
    """审批规则"""
    
    RULE_TYPE_CHOICES = [
        ('single', '单人审批'),
        ('any', '任意一人审批'),
        ('all', '全部审批'),
        ('sequential', '顺序审批'),
    ]
    
    name = models.CharField(max_length=64, verbose_name="规则名称")
    code = models.CharField(max_length=32, unique=True, verbose_name="规则编码")
    environment = models.CharField(max_length=32, verbose_name="适用环境")
    rule_type = models.CharField(
        max_length=32, choices=RULE_TYPE_CHOICES,
        verbose_name="规则类型"
    )
    
    # 审批人配置: [{"id": 1, "name": "张三", "order": 1}]
    approvers = models.JSONField(default=list, verbose_name="审批人列表")
    
    # 条件配置
    min_approvers = models.IntegerField(default=1, verbose_name="最少审批人数")
    
    # 状态
    status = models.IntegerField(
        choices=CommonStatus.choices,
        default=CommonStatus.ENABLED,
        verbose_name="状态"
    )
    
    class Meta:
        db_table = "release_approval_rule"
        verbose_name = "审批规则"
        verbose_name_plural = verbose_name
        ordering = ["-create_time"]

    def __str__(self):
        return self.name
