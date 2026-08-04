# -*- coding: utf-8 -*-
"""
发布管理过滤器
"""
import django_filters
from .models import (
    Project, Module, Application, CodeRepository, ConfigPackage, SyncLog,
    PipelineTemplate, PipelineTemplateVersion,
    ApplicationPipelineConfig, ApplicationPipelineVersion,
    ReleaseRecord, ReleaseBuildLog, ApprovalRule
)


class ProjectFilter(django_filters.FilterSet):
    """项目过滤器"""
    name = django_filters.CharFilter(lookup_expr='icontains')
    code = django_filters.CharFilter(lookup_expr='icontains')
    status = django_filters.NumberFilter()

    class Meta:
        model = Project
        fields = ['name', 'code', 'status']


class CodeRepositoryFilter(django_filters.FilterSet):
    """代码仓库过滤器"""
    name = django_filters.CharFilter(lookup_expr='icontains')
    code = django_filters.CharFilter(lookup_expr='icontains')
    project = django_filters.NumberFilter()
    module = django_filters.NumberFilter()
    module__isnull = django_filters.BooleanFilter(field_name='module', lookup_expr='isnull')
    repository_type = django_filters.CharFilter()
    status = django_filters.NumberFilter()

    class Meta:
        model = CodeRepository
        fields = ['name', 'code', 'project', 'module', 'module__isnull', 'repository_type', 'status']


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
    code_repository = django_filters.NumberFilter(field_name='code_repository_id')
    app_type = django_filters.CharFilter()
    status = django_filters.NumberFilter()

    class Meta:
        model = Application
        fields = ['name', 'code', 'project', 'module', 'code_repository', 'app_type', 'status']


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


# ============================================================
# 流水线模板系统过滤器
# ============================================================

class PipelineTemplateFilter(django_filters.FilterSet):
    """流水线模板过滤器"""
    name = django_filters.CharFilter(lookup_expr='icontains')
    code = django_filters.CharFilter(lookup_expr='icontains')
    language = django_filters.CharFilter(lookup_expr='icontains')
    framework = django_filters.CharFilter(lookup_expr='icontains')
    is_official = django_filters.BooleanFilter()
    status = django_filters.NumberFilter()

    class Meta:
        model = PipelineTemplate
        fields = ['name', 'code', 'language', 'framework', 'is_official', 'status']


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
    environment = django_filters.CharFilter()
    template = django_filters.NumberFilter(field_name='template_id')
    is_active = django_filters.BooleanFilter()

    class Meta:
        model = ApplicationPipelineConfig
        fields = ['application', 'environment', 'template', 'is_active']


class ApplicationPipelineVersionFilter(django_filters.FilterSet):
    """应用配置版本过滤器"""
    config = django_filters.NumberFilter(field_name='config_id')
    version = django_filters.NumberFilter()
    generated_by = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = ApplicationPipelineVersion
        fields = ['config', 'version', 'generated_by']


# ============================================================
# 发布管理相关过滤器
# ============================================================

class ReleaseRecordFilter(django_filters.FilterSet):
    """发布记录过滤器"""
    application = django_filters.NumberFilter(field_name='application_id')
    application_name = django_filters.CharFilter(field_name='application__name', lookup_expr='icontains')
    project = django_filters.NumberFilter(field_name='application__project_id')
    module = django_filters.NumberFilter(field_name='application__module_id')
    environment = django_filters.CharFilter()
    status = django_filters.CharFilter()
    branch = django_filters.CharFilter(lookup_expr='icontains')
    version = django_filters.CharFilter(lookup_expr='icontains')
    released_by = django_filters.CharFilter(lookup_expr='icontains')
    start_date = django_filters.DateFilter(field_name='create_time__date', lookup_expr='gte')
    end_date = django_filters.DateFilter(field_name='create_time__date', lookup_expr='lte')

    class Meta:
        model = ReleaseRecord
        fields = ['application', 'application_name', 'project', 'module', 'environment', 'status', 'branch', 'version', 'released_by', 'start_date', 'end_date']


class ReleaseBuildLogFilter(django_filters.FilterSet):
    """构建日志过滤器"""
    release = django_filters.NumberFilter(field_name='release_id')
    log_type = django_filters.CharFilter()
    stage_name = django_filters.CharFilter(lookup_expr='icontains')
    stage_status = django_filters.CharFilter()

    class Meta:
        model = ReleaseBuildLog
        fields = ['release', 'log_type', 'stage_name', 'stage_status']


class ApprovalRuleFilter(django_filters.FilterSet):
    """审批规则过滤器（支持三级作用域过滤）"""
    name = django_filters.CharFilter(lookup_expr='icontains')
    code = django_filters.CharFilter(lookup_expr='icontains')
    environment = django_filters.CharFilter()
    rule_type = django_filters.CharFilter()
    status = django_filters.NumberFilter()
    project = django_filters.NumberFilter(field_name='project_id')
    application = django_filters.NumberFilter(field_name='application_id')
    # 作用域筛选：application/project/global
    scope = django_filters.CharFilter(method='filter_scope')

    class Meta:
        model = ApprovalRule
        fields = ['name', 'code', 'environment', 'rule_type', 'status', 'project', 'application']

    def filter_scope(self, queryset, name, value):
        """按作用域层级过滤"""
        if value == 'global':
            return queryset.filter(project__isnull=True, application__isnull=True)
        elif value == 'project':
            return queryset.filter(project__isnull=False, application__isnull=True)
        elif value == 'application':
            return queryset.filter(application__isnull=False)
        return queryset
