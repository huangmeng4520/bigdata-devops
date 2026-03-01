# -*- coding: utf-8 -*-
"""
发布管理过滤器
"""
import django_filters
from .models import Project, Module, Application, ConfigPackage, SyncLog, Template


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
