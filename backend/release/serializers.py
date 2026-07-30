# -*- coding: utf-8 -*-
"""
发布管理序列化器
"""
from rest_framework import serializers
from .models import (
    Project, Module, Application, CodeRepository, ConfigPackage, SyncLog,
    PipelineTemplate, PipelineTemplateVersion,
    ApplicationPipelineConfig, ApplicationPipelineVersion,
    EnvironmentStrategy,
    ReleaseRecord, ReleaseBuildLog, ApprovalRule
)


class ProjectSerializer(serializers.ModelSerializer):
    """项目序列化器"""
    module_count = serializers.SerializerMethodField()
    app_count = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    gitlab_group_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Project
        fields = "__all__"
        read_only_fields = ["creator", "modifier", "create_time", "update_time"]

    def get_module_count(self, obj):
        return obj.modules.filter(is_deleted=False).count()

    def get_app_count(self, obj):
        return obj.applications.filter(is_deleted=False).count()

    def get_gitlab_group_url(self, obj):
        if not obj.gitlab_group_id:
            return None
        from release.services.base import ConfigService
        gitlab_url = ConfigService.get(ConfigService.GITLAB_URL, default="")
        if not gitlab_url:
            return None
        return f"{gitlab_url.rstrip('/')}/{obj.code}"


class ProjectCreateSerializer(serializers.ModelSerializer):
    """项目创建序列化器"""
    class Meta:
        model = Project
        fields = ["name", "code", "description", "status", "sort"]


class ModuleSerializer(serializers.ModelSerializer):
    """模块序列化器"""
    project_name = serializers.CharField(source="project.name", read_only=True)
    app_count = serializers.SerializerMethodField()
    repo_count = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    gitlab_subgroup_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Module
        fields = "__all__"
        read_only_fields = ["creator", "modifier", "create_time", "update_time"]

    def get_app_count(self, obj):
        return obj.applications.filter(is_deleted=False).count()

    def get_repo_count(self, obj):
        return obj.code_repositories.filter(is_deleted=False).count()

    def get_gitlab_subgroup_url(self, obj):
        if not obj.gitlab_subgroup_id:
            return None
        from release.services.base import ConfigService
        gitlab_url = ConfigService.get(ConfigService.GITLAB_URL, default="")
        if not gitlab_url:
            return None
        return f"{gitlab_url.rstrip('/')}/{obj.project.code}/{obj.code}"


class ModuleCreateSerializer(serializers.ModelSerializer):
    """模块创建序列化器"""
    class Meta:
        model = Module
        fields = ["project", "name", "code", "description", "gitlab_subgroup_id", "status", "sort", "remark"]


class ApplicationSerializer(serializers.ModelSerializer):
    """应用序列化器"""
    project_name = serializers.CharField(source="project.name", read_only=True)
    module_name = serializers.CharField(source="module.name", read_only=True)
    app_type_display = serializers.CharField(source="get_app_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    jenkins_sync_status_display = serializers.CharField(source="get_jenkins_sync_status_display", read_only=True)
    gitlab_sync_status_display = serializers.CharField(source="get_gitlab_sync_status_display", read_only=True)
    harbor_sync_status_display = serializers.CharField(source="get_harbor_sync_status_display", read_only=True)
    code_repository_name = serializers.CharField(source="code_repository.name", read_only=True)
    code_repository_git_url = serializers.CharField(source="code_repository.git_url", read_only=True)
    pipeline_sync_summary = serializers.SerializerMethodField(read_only=True)

    def get_pipeline_sync_summary(self, obj):
        """各环境流水线配置同步状态明细，供前端展示聚合状态与 Tooltip"""
        configs = obj.pipeline_configs.filter(is_active=True, is_deleted=False)
        return [
            {
                'environment': c.environment,
                'environment_display': c.get_environment_display(),
                'jenkins_sync_status': c.jenkins_sync_status,
                'jenkins_sync_status_display': c.get_jenkins_sync_status_display(),
                'config_dirty': c.config_dirty,
                'jenkins_job_name': c.jenkins_job_name,
            }
            for c in configs
        ]

    class Meta:
        model = Application
        fields = "__all__"
        read_only_fields = [
            "creator", "modifier", "create_time", "update_time",
            "git_url", "gitlab_project_id", "harbor_project",
            "jenkins_sync_status", "jenkins_sync_time", "jenkins_sync_message",
            "gitlab_sync_status", "gitlab_sync_time", "gitlab_sync_message",
            "harbor_sync_status", "harbor_sync_time", "harbor_sync_message"
        ]


class CodeRepositorySerializer(serializers.ModelSerializer):
    """代码仓库序列化器"""
    project_name = serializers.CharField(source="project.name", read_only=True)
    module_name = serializers.CharField(source="module.name", read_only=True)
    app_count = serializers.SerializerMethodField()
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    repository_type_display = serializers.CharField(source="get_repository_type_display", read_only=True)

    def get_app_count(self, obj):
        return obj.applications.filter(is_deleted=False).count()

    class Meta:
        model = CodeRepository
        fields = "__all__"
        read_only_fields = ["creator", "modifier", "create_time", "update_time", "gitlab_project_id", "git_url", "git_http_url"]


class CodeRepositoryCreateSerializer(serializers.ModelSerializer):
    """代码仓库创建序列化器"""
    class Meta:
        model = CodeRepository
        fields = [
            "project", "module", "name", "code", "repository_type",
            "default_branch", "status", "description"
        ]
        read_only_fields = ["git_url", "git_http_url"]


class ApplicationCreateSerializer(serializers.ModelSerializer):
    """应用创建序列化器"""
    class Meta:
        model = Application
        fields = [
            "project", "module", "name", "code", "description",
            "app_type", "build_command", "build_branch", "dockerfile_path",
            "status", "sort", "code_repository", "code_subpath"
        ]

    def create(self, validated_data):
        instance = super().create(validated_data)
        # 从关联的代码仓库中获取 git_url
        if instance.code_repository and instance.code_repository.git_url:
            instance.git_url = instance.code_repository.git_url
            instance.gitlab_project_id = instance.code_repository.gitlab_project_id
            instance.save(update_fields=['git_url', 'gitlab_project_id'])
        return instance

    def validate(self, data):
        """验证模块是否属于所选项目"""
        module = data.get('module')
        project = data.get('project')
        code = data.get('code')
        
        # 模块是可选的，只有当选择了模块时才验证
        if module and project and module.project_id != project.id:
            raise serializers.ValidationError({"module": "模块不属于所选项目"})

        # 验证应用代码唯一性
        if project and code:
            queryset = Application.objects.filter(
                project=project, code=code, is_deleted=False
            )
            if module:
                queryset = queryset.filter(module=module)
                # 更新时排除自身
                if self.instance:
                    queryset = queryset.exclude(pk=self.instance.pk)
                exists = queryset.exists()
                if exists:
                    raise serializers.ValidationError({"code": "该模块下已存在相同编码的应用"})
            else:
                queryset = queryset.filter(module__isnull=True)
                # 更新时排除自身
                if self.instance:
                    queryset = queryset.exclude(pk=self.instance.pk)
                exists = queryset.exists()
                if exists:
                    raise serializers.ValidationError({"code": "该项目下（无模块）已存在相同编码的应用"})

        return data


class ConfigPackageSerializer(serializers.ModelSerializer):
    """配置包序列化器"""
    app_name = serializers.CharField(source="app.name", read_only=True)
    sync_status_display = serializers.CharField(source="get_sync_status_display", read_only=True)

    class Meta:
        model = ConfigPackage
        fields = "__all__"
        read_only_fields = ["creator", "create_time", "update_time"]


class SyncLogSerializer(serializers.ModelSerializer):
    """同步日志序列化器"""
    project_name = serializers.CharField(source="project.name", read_only=True)
    module_name = serializers.CharField(source="module.name", read_only=True)
    app_name = serializers.CharField(source="app.name", read_only=True)
    sync_type_display = serializers.CharField(source="get_sync_type_display", read_only=True)
    action_display = serializers.CharField(source="get_action_display", read_only=True)

    class Meta:
        model = SyncLog
        fields = "__all__"
        read_only_fields = ["create_time"]


# ============================================================
# 流水线模板系统序列化器
# ============================================================

class PipelineTemplateVersionSerializer(serializers.ModelSerializer):
    """模板版本序列化器"""
    template_name = serializers.CharField(source="template.name", read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = PipelineTemplateVersion
        fields = "__all__"
        read_only_fields = ["creator", "modifier", "create_time", "update_time"]


class PipelineTemplateVersionCreateSerializer(serializers.ModelSerializer):
    """模板版本创建序列化器"""
    template = serializers.PrimaryKeyRelatedField(
        queryset=PipelineTemplate.objects.all(),
        required=False,
        allow_null=True
    )

    class Meta:
        model = PipelineTemplateVersion
        fields = ["template", "version", "content", "variables", "stages", "stages_content", "change_log", "is_latest", "status"]
        extra_kwargs = {
            'template': {'required': False, 'allow_null': True},
        }


class PipelineTemplateSerializer(serializers.ModelSerializer):
    """流水线模板序列化器"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    version_count = serializers.SerializerMethodField()
    latest_version = serializers.SerializerMethodField()

    class Meta:
        model = PipelineTemplate
        fields = "__all__"
        read_only_fields = ["creator", "modifier", "create_time", "update_time"]

    def get_version_count(self, obj):
        return obj.versions.filter(is_deleted=False).count()

    def get_latest_version(self, obj):
        latest = obj.latest_version
        if latest:
            return {"id": latest.id, "version": latest.version}
        return None


class PipelineTemplateCreateSerializer(serializers.ModelSerializer):
    """流水线模板创建序列化器"""
    name = serializers.CharField(required=True, min_length=1)
    code = serializers.CharField(required=True, min_length=1)
    language = serializers.CharField(required=True, min_length=1)
    language_version = serializers.CharField(required=False, allow_blank=True, default='')
    framework = serializers.CharField(required=False, allow_blank=True, default='')
    description = serializers.CharField(required=False, allow_blank=True, default='')

    class Meta:
        model = PipelineTemplate
        fields = ["id", "name", "code", "language", "language_version", "framework", "description", "is_official", "status"]
        read_only_fields = ["id"]

    def validate_code(self, value):
        """验证 code 唯一性"""
        if not value:
            raise serializers.ValidationError("模板编码不能为空")
        # 检查是否已存在（排除当前记录）
        queryset = PipelineTemplate.objects.filter(code=value, is_deleted=False)
        if self.instance:
            queryset = queryset.exclude(id=self.instance.id)
        if queryset.exists():
            raise serializers.ValidationError(f"模板编码 '{value}' 已存在")
        return value


class PipelineTemplateDetailSerializer(PipelineTemplateSerializer):
    """流水线模板详情序列化器（包含版本列表）"""
    versions = PipelineTemplateVersionSerializer(many=True, read_only=True)

    class Meta(PipelineTemplateSerializer.Meta):
        pass


class ApplicationPipelineVersionSerializer(serializers.ModelSerializer):
    """应用配置版本序列化器"""
    config_name = serializers.SerializerMethodField()
    generated_by_name = serializers.CharField(source="generated_by", read_only=True)

    class Meta:
        model = ApplicationPipelineVersion
        fields = "__all__"
        read_only_fields = ["create_time", "update_time"]

    def get_config_name(self, obj):
        return str(obj.config)


class ApplicationPipelineConfigSerializer(serializers.ModelSerializer):
    """应用流水线配置序列化器"""
    application_name = serializers.CharField(source="application.name", read_only=True)
    environment_display = serializers.CharField(source='get_environment_display', read_only=True)
    template_name = serializers.CharField(source="template.name", read_only=True)
    template_version_name = serializers.SerializerMethodField()
    version_count = serializers.SerializerMethodField()
    jenkins_sync_status_display = serializers.CharField(source='get_jenkins_sync_status_display', read_only=True)

    class Meta:
        model = ApplicationPipelineConfig
        fields = "__all__"
        read_only_fields = [
            "creator", "modifier", "create_time", "update_time", "current_version",
            "jenkins_sync_status", "jenkins_sync_time", "jenkins_sync_message", "jenkins_job_name"
        ]

    def get_template_version_name(self, obj):
        if obj.template_version:
            return f"v{obj.template_version.version}"
        return None

    def get_version_count(self, obj):
        return obj.versions.count()


class ApplicationPipelineConfigCreateSerializer(serializers.ModelSerializer):
    """应用流水线配置创建序列化器"""
    class Meta:
        model = ApplicationPipelineConfig
        fields = [
            "application", "environment", "template", "template_version",
            "variables", "stages_config", "is_active"
        ]
        validators = []


class EnvironmentStrategySerializer(serializers.ModelSerializer):
    """环境策略序列化器"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = EnvironmentStrategy
        fields = "__all__"
        read_only_fields = ["creator", "modifier", "create_time", "update_time"]


class EnvironmentStrategyCreateSerializer(serializers.ModelSerializer):
    """环境策略创建序列化器"""
    name = serializers.CharField(required=False, allow_blank=True, default='')
    code = serializers.CharField(required=False, allow_blank=True, default='')
    description = serializers.CharField(required=False, allow_blank=True, default='')

    class Meta:
        model = EnvironmentStrategy
        fields = [
            "name", "code", "environment",
            "requires_approval", "auto_deploy", "description", "is_default", "status"
        ]


# ============================================================
# 命名验证相关序列化器
# ============================================================

class ValidateNamingSerializer(serializers.Serializer):
    """命名验证序列化器"""
    type = serializers.ChoiceField(choices=['project', 'module', 'app'], help_text="命名类型")
    name = serializers.CharField(max_length=64, help_text="名称")


class GenerateNamesSerializer(serializers.Serializer):
    """生成标准化名称序列化器"""
    project = serializers.CharField(max_length=32, help_text="项目编码")
    module = serializers.CharField(max_length=32, help_text="模块编码")
    app = serializers.CharField(max_length=64, help_text="应用编码")
    version = serializers.CharField(max_length=32, required=False, default="latest", help_text="版本号")
    environment = serializers.CharField(max_length=32, required=False, default="dev", help_text="环境")


# ============================================================
# 发布管理相关序列化器
# ============================================================

class ReleaseRecordSerializer(serializers.ModelSerializer):
    """发布记录序列化器"""
    application_name = serializers.CharField(source="application.name", read_only=True)
    application_code = serializers.CharField(source="application.code", read_only=True)
    project_name = serializers.CharField(source="application.project.name", read_only=True)
    module_name = serializers.CharField(source="application.module.name", read_only=True)
    environment_display = serializers.CharField(source='get_environment_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = ReleaseRecord
        fields = "__all__"
        read_only_fields = [
            "creator", "modifier", "create_time", "update_time",
            "jenkins_build_number", "jenkins_build_url", "jenkins_build_status",
            "jenkins_build_duration", "docker_image", "artifact_url",
            "conversation_id",
        ]


class ReleaseCreateSerializer(serializers.Serializer):
    """发布创建序列化器"""
    branch = serializers.CharField(max_length=128, help_text="代码分支")
    environment = serializers.CharField(max_length=32, help_text="目标环境")
    version = serializers.CharField(max_length=64, required=False, allow_null=True, default=None, help_text="发布版本")
    require_approval = serializers.BooleanField(default=False, help_text="需要审批")
    approval_type = serializers.CharField(max_length=32, required=False, allow_null=True, default=None, help_text="审批类型")
    approvers = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        default=list,
        help_text="审批人列表"
    )
    remark = serializers.CharField(required=False, allow_blank=True, default='', help_text="发布说明")


class ReleaseBuildLogSerializer(serializers.ModelSerializer):
    """构建日志序列化器"""
    release_info = serializers.SerializerMethodField()

    class Meta:
        model = ReleaseBuildLog
        fields = "__all__"
        read_only_fields = ["create_time"]

    def get_release_info(self, obj):
        return {
            "application": obj.release.application.name,
            "build_number": obj.release.jenkins_build_number,
        }


class ApprovalRuleSerializer(serializers.ModelSerializer):
    """审批规则序列化器"""
    rule_type_display = serializers.CharField(source='get_rule_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = ApprovalRule
        fields = "__all__"
        read_only_fields = ["creator", "modifier", "create_time", "update_time"]


class ApprovalRuleCreateSerializer(serializers.ModelSerializer):
    """审批规则创建序列化器"""
    class Meta:
        model = ApprovalRule
        fields = ["name", "code", "environment", "rule_type", "approvers", "min_approvers", "status"]


class ApprovalActionSerializer(serializers.Serializer):
    """审批操作序列化器"""
    approved = serializers.BooleanField(help_text="是否批准")
    comment = serializers.CharField(max_length=512, required=False, allow_blank=True, default='', help_text="审批意见")
