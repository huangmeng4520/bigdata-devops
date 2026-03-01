# -*- coding: utf-8 -*-
from django.contrib import admin
from .models import Project, Module, Application, ConfigPackage, SyncLog, Template


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'code', 'status', 'sort', 'create_time']
    list_filter = ['status']
    search_fields = ['name', 'code']
    ordering = ['-sort', '-create_time']


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'code', 'project', 'status', 'sort', 'create_time']
    list_filter = ['status', 'project']
    search_fields = ['name', 'code']
    ordering = ['-sort', '-create_time']


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'code', 'project', 'module', 'app_type', 'status', 'create_time']
    list_filter = ['status', 'app_type', 'project']
    search_fields = ['name', 'code']
    ordering = ['-sort', '-create_time']


@admin.register(ConfigPackage)
class ConfigPackageAdmin(admin.ModelAdmin):
    list_display = ['id', 'app', 'version', 'file_size', 'sync_status', 'sync_time', 'create_time']
    list_filter = ['sync_status']
    search_fields = ['app__name', 'version']
    ordering = ['-create_time']


@admin.register(SyncLog)
class SyncLogAdmin(admin.ModelAdmin):
    list_display = ['id', 'sync_type', 'resource_name', 'action', 'status', 'create_time']
    list_filter = ['sync_type', 'action', 'status']
    search_fields = ['resource_name']
    ordering = ['-create_time']


@admin.register(Template)
class TemplateAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'code', 'template_type', 'app_type', 'status', 'create_time']
    list_filter = ['status', 'template_type', 'app_type']
    search_fields = ['name', 'code']
    ordering = ['-create_time']
