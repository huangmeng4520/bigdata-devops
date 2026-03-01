# -*- coding: utf-8 -*-
"""
发布管理序列化器
"""
from rest_framework import serializers
from .models import Project, Module, Application, ConfigPackage, SyncLog, Template


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

    class Meta:
        model = Application
        fields = "__all__"
        read_only_fields = [
            "creator", "modifier", "create_time", "update_time",
            "git_url", "gitlab_project_id", "jenkins_ci_job", "jenkins_cd_job", "harbor_project"
        ]


class ApplicationCreateSerializer(serializers.ModelSerializer):
    """应用创建序列化器"""
    class Meta:
        model = Application
        fields = [
            "project", "module", "name", "code", "description",
            "app_type", "build_branch", "dockerfile_path", "status", "sort"
        ]

    def validate(self, data):
        """验证模块是否属于所选项目"""
        module = data.get('module')
        project = data.get('project')
        if module and project and module.project_id != project.id:
            raise serializers.ValidationError({"module": "模块不属于所选项目"})
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
