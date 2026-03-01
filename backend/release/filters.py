# -*- coding: utf-8 -*-
"""
发布管理过滤器
"""
import django_filters
from .models import (
    Project, Module, Application, ConfigPackage, SyncLog, Template,
    PipelineTemplate, PipelineTemplateVersion,
    ApplicationPipelineConfig, ApplicationPipelineVersion,
    EnvironmentStrategy, CDConfigExport
)


class ProjectFilter(django_filters.FilterSet):
    """项目过滤器"""
    name = django_filters.CharFilter(lookup_expr='icontains')
    code = django_filters.CharFilter(lookup_expr='icontains')
    status = django_filters.NumberFilter()

    class Meta:
        model = Project
        fields = ['name', 'code', 'status']


class ModuleFilter(django_filters.FilterSet):
    """模块过滤器"""
    name = django_filters.CharFilter(lookup_expr='icontains')
    code = django_filters.CharFilter(lookup_expr='icontains')
    project = django_filters.NumberFilter(field_name='project_id')
    status = django_filters.NumberFilter()

    class Meta:
        model = Module
        fields = ['name', 'code', 'project', 'status']


class ApplicationFilter(django_filters.FilterSet):
    """应用过滤器"""
    name = django_filters.CharFilter(lookup_expr='icontains')
    code = django_filters.CharFilter(lookup_expr='icontains')
    project = django_filters.NumberFilter(field_name='project_id')
    module = django_filters.NumberFilter(field_name='module_id')
    app_type = django_filters.CharFilter()
    status = django_filters.NumberFilter()

    class Meta:
        model = Application
        fields = ['name', 'code', 'project', 'module', 'app_type', 'status']


class ConfigPackageFilter(django_filters.FilterSet):
    """配置包过滤器"""
    app = django_filters.NumberFilter(field_name='app_id')
    sync_status = django_filters.NumberFilter()

    class Meta:
        model = ConfigPackage
        fields = ['app', 'sync_status']


class SyncLogFilter(django_filters.FilterSet):
    """同步日志过滤器"""
    sync_type = django_filters.CharFilter()
    action = django_filters.CharFilter()
    status = django_filters.NumberFilter()
    project = django_filters.NumberFilter(field_name='project_id')
    module = django_filters.NumberFilter(field_name='module_id')
    app = django_filters.NumberFilter(field_name='app_id')

    class Meta:
        model = SyncLog
        fields = ['sync_type', 'action', 'status', 'project', 'module', 'app']


class TemplateFilter(django_filters.FilterSet):
    """模板过滤器"""
    name = django_filters.CharFilter(lookup_expr='icontains')
    code = django_filters.CharFilter(lookup_expr='icontains')
    template_type = django_filters.CharFilter()
    app_type = django_filters.CharFilter()
    status = django_filters.NumberFilter()

    class Meta:
        model = Template
        fields = ['name', 'code', 'template_type', 'app_type', 'status']


# ============================================================
# CI/CD 模板系统过滤器
# ============================================================

class PipelineTemplateFilter(django_filters.FilterSet):
    """流水线模板过滤器"""
    name = django_filters.CharFilter(lookup_expr='icontains')
    code = django_filters.CharFilter(lookup_expr='icontains')
    template_type = django_filters.CharFilter()
    language = django_filters.CharFilter(lookup_expr='icontains')
    framework = django_filters.CharFilter(lookup_expr='icontains')
    is_official = django_filters.BooleanFilter()
    status = django_filters.NumberFilter()

    class Meta:
        model = PipelineTemplate
        fields = ['name', 'code', 'template_type', 'language', 'framework', 'is_official', 'status']


class PipelineTemplateVersionFilter(django_filters.FilterSet):
    """模板版本过滤器"""
    template = django_filters.NumberFilter(field_name='template_id')
    version = django_filters.CharFilter(lookup_expr='icontains')
    is_latest = django_filters.BooleanFilter()
    status = django_filters.NumberFilter()

    class Meta:
        model = PipelineTemplateVersion
        fields = ['template', 'version', 'is_latest', 'status']


class ApplicationPipelineConfigFilter(django_filters.FilterSet):
    """应用流水线配置过滤器"""
    application = django_filters.NumberFilter(field_name='application_id')
    config_type = django_filters.CharFilter()
    environment = django_filters.CharFilter()
    template = django_filters.NumberFilter(field_name='template_id')
    is_active = django_filters.BooleanFilter()

    class Meta:
        model = ApplicationPipelineConfig
        fields = ['application', 'config_type', 'environment', 'template', 'is_active']


class ApplicationPipelineVersionFilter(django_filters.FilterSet):
    """应用配置版本过滤器"""
    config = django_filters.NumberFilter(field_name='config_id')
    version = django_filters.NumberFilter()
    generated_by = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = ApplicationPipelineVersion
        fields = ['config', 'version', 'generated_by']


class EnvironmentStrategyFilter(django_filters.FilterSet):
    """环境策略过滤器"""
    name = django_filters.CharFilter(lookup_expr='icontains')
    code = django_filters.CharFilter(lookup_expr='icontains')
    environment = django_filters.CharFilter()
    pipeline_mode = django_filters.CharFilter()
    is_default = django_filters.BooleanFilter()
    status = django_filters.NumberFilter()

    class Meta:
        model = EnvironmentStrategy
        fields = ['name', 'code', 'environment', 'pipeline_mode', 'is_default', 'status']


class CDConfigExportFilter(django_filters.FilterSet):
    """CD配置导出过滤器"""
    application = django_filters.NumberFilter(field_name='application_id')
    environment = django_filters.CharFilter()
    config_version = django_filters.NumberFilter()
    export_format = django_filters.CharFilter()
    exported_by = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = CDConfigExport
        fields = ['application', 'environment', 'config_version', 'export_format', 'exported_by']
