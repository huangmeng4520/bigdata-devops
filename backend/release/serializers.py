# -*- coding: utf-8 -*-
"""
发布管理序列化器
"""
from rest_framework import serializers
from .models import (
    Project, Module, Application, ConfigPackage, SyncLog, Template,
    PipelineTemplate, PipelineTemplateVersion,
    ApplicationPipelineConfig, ApplicationPipelineVersion,
    EnvironmentStrategy, CDConfigExport,
    ReleaseRecord, ReleaseBuildLog, ApprovalRule
)


class ProjectSerializer(serializers.ModelSerializer):
    """项目序列化器"""
    module_count = serializers.SerializerMethodField()
    app_count = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Project
        fields = "__all__"
        read_only_fields = ["creator", "modifier", "create_time", "update_time"]

    def get_module_count(self, obj):
        return obj.modules.filter(is_deleted=False).count()

    def get_app_count(self, obj):
        return obj.applications.filter(is_deleted=False).count()


class ProjectCreateSerializer(serializers.ModelSerializer):
    """项目创建序列化器"""
    class Meta:
        model = Project
        fields = ["name", "code", "description", "status", "sort"]


class ModuleSerializer(serializers.ModelSerializer):
    """模块序列化器"""
    project_name = serializers.CharField(source="project.name", read_only=True)
    app_count = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Module
        fields = "__all__"
        read_only_fields = ["creator", "modifier", "create_time", "update_time"]

    def get_app_count(self, obj):
        return obj.applications.filter(is_deleted=False).count()


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
    ci_template_name = serializers.CharField(source="ci_template.name", read_only=True)
    cd_template_name = serializers.CharField(source="cd_template.name", read_only=True)
    jenkins_sync_status_display = serializers.CharField(source="get_jenkins_sync_status_display", read_only=True)
    gitlab_sync_status_display = serializers.CharField(source="get_gitlab_sync_status_display", read_only=True)
    harbor_sync_status_display = serializers.CharField(source="get_harbor_sync_status_display", read_only=True)

    class Meta:
        model = Application
        fields = "__all__"
        read_only_fields = [
            "creator", "modifier", "create_time", "update_time",
            "git_url", "gitlab_project_id", "jenkins_ci_job", "jenkins_cd_job", "harbor_project",
            "jenkins_sync_status", "jenkins_sync_time", "jenkins_sync_message",
            "gitlab_sync_status", "gitlab_sync_time", "gitlab_sync_message",
            "harbor_sync_status", "harbor_sync_time", "harbor_sync_message"
        ]


class ApplicationCreateSerializer(serializers.ModelSerializer):
    """应用创建序列化器"""
    class Meta:
        model = Application
        fields = [
            "project", "module", "name", "code", "description",
            "app_type", "build_branch", "dockerfile_path", "status", "sort",
            "ci_template", "cd_template", "ci_variables", "cd_variables"
        ]

    def validate(self, data):
        """验证模块是否属于所选项目"""
        module = data.get('module')
        project = data.get('project')
        if module and project and module.project_id != project.id:
            raise serializers.ValidationError({"module": "模块不属于所选项目"})

        # 验证 CI 模板类型
        ci_template = data.get('ci_template')
        if ci_template and ci_template.template_type != 'ci':
            raise serializers.ValidationError({"ci_template": "CI 模板类型不正确"})

        # 验证 CD 模板类型
        cd_template = data.get('cd_template')
        if cd_template and cd_template.template_type != 'cd':
            raise serializers.ValidationError({"cd_template": "CD 模板类型不正确"})

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


class TemplateSerializer(serializers.ModelSerializer):
    """发布模板序列化器"""
    template_type_display = serializers.CharField(source="get_template_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Template
        fields = "__all__"
        read_only_fields = ["creator", "modifier", "create_time", "update_time"]


class TemplateCreateSerializer(serializers.ModelSerializer):
    """发布模板创建序列化器"""
    class Meta:
        model = Template
        fields = ["name", "code", "template_type", "app_type", "content", "description", "status"]


# ============================================================
# CI/CD 模板系统序列化器
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
    template_type_display = serializers.CharField(source='get_template_type_display', read_only=True)
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
    template_type = serializers.CharField(required=True)
    language = serializers.CharField(required=True, min_length=1)
    language_version = serializers.CharField(required=False, allow_blank=True, default='')
    framework = serializers.CharField(required=False, allow_blank=True, default='')
    description = serializers.CharField(required=False, allow_blank=True, default='')

    class Meta:
        model = PipelineTemplate
        fields = ["id", "name", "code", "template_type", "language", "language_version", "framework", "description", "is_official", "status"]
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
    config_type_display = serializers.CharField(source='get_config_type_display', read_only=True)
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
            "application", "config_type", "environment", "template", "template_version",
            "custom_content", "variables", "stages_config", "is_active"
        ]


class EnvironmentStrategySerializer(serializers.ModelSerializer):
    """环境策略序列化器"""
    pipeline_mode_display = serializers.CharField(source='get_pipeline_mode_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = EnvironmentStrategy
        fields = "__all__"
        read_only_fields = ["creator", "modifier", "create_time", "update_time"]


class EnvironmentStrategyCreateSerializer(serializers.ModelSerializer):
    """环境策略创建序列化器"""
    name = serializers.CharField(required=False, allow_blank=True, default='')
    code = serializers.CharField(required=False, allow_blank=True, default='')
    ci_jenkins = serializers.CharField(required=False, allow_blank=True, default='')
    cd_jenkins = serializers.CharField(required=False, allow_blank=True, default='')
    description = serializers.CharField(required=False, allow_blank=True, default='')

    class Meta:
        model = EnvironmentStrategy
        fields = [
            "name", "code", "environment", "pipeline_mode", "ci_jenkins", "cd_jenkins",
            "requires_approval", "auto_deploy", "description", "is_default", "status"
        ]


class CDConfigExportSerializer(serializers.ModelSerializer):
    """CD配置导出序列化器"""
    application_name = serializers.CharField(source="application.name", read_only=True)
    export_format_display = serializers.CharField(source='get_export_format_display', read_only=True)
    exported_by_name = serializers.CharField(source="exported_by", read_only=True)

    class Meta:
        model = CDConfigExport
        fields = "__all__"
        read_only_fields = ["creator", "create_time", "update_time", "download_count"]


class CDConfigExportCreateSerializer(serializers.ModelSerializer):
    """CD配置导出创建序列化器"""
    class Meta:
        model = CDConfigExport
        fields = ["application", "environment", "config_version", "export_format", "content", "file_path", "exported_by"]


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
            "jenkins_build_duration", "docker_image", "artifact_url"
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
