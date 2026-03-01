# -*- coding: utf-8 -*-
"""
发布管理路由配置
"""
from django.urls import include, path
from rest_framework import routers

from . import views

router = routers.DefaultRouter()
# 原有路由
router.register(r'project', views.ProjectViewSet, basename='release-project')
router.register(r'module', views.ModuleViewSet, basename='release-module')
router.register(r'application', views.ApplicationViewSet, basename='release-application')
router.register(r'config-package', views.ConfigPackageViewSet, basename='release-config-package')
router.register(r'sync-log', views.SyncLogViewSet, basename='release-sync-log')
router.register(r'template', views.TemplateViewSet, basename='release-template')

# CI/CD 模板系统路由
router.register(r'pipeline-templates', views.PipelineTemplateViewSet, basename='release-pipeline-template')
router.register(r'pipeline-template-versions', views.PipelineTemplateVersionViewSet, basename='release-pipeline-template-version')
router.register(r'application-pipeline-configs', views.ApplicationPipelineConfigViewSet, basename='release-application-pipeline-config')
router.register(r'application-pipeline-versions', views.ApplicationPipelineVersionViewSet, basename='release-application-pipeline-version')
router.register(r'environment-strategies', views.EnvironmentStrategyViewSet, basename='release-environment-strategy')
router.register(r'cd-exports', views.CDConfigExportViewSet, basename='release-cd-export')


urlpatterns = [
    path('', include(router.urls)),
]
