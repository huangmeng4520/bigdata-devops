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
router.register(r'code-repository', views.CodeRepositoryViewSet, basename='release-code-repository')
router.register(r'config-package', views.ConfigPackageViewSet, basename='release-config-package')
router.register(r'sync-log', views.SyncLogViewSet, basename='release-sync-log')
    # 流水线模板系统路由
router.register(r'pipeline-templates', views.PipelineTemplateViewSet, basename='release-pipeline-template')
router.register(r'pipeline-template-versions', views.PipelineTemplateVersionViewSet, basename='release-pipeline-template-version')
router.register(r'application-pipeline-configs', views.ApplicationPipelineConfigViewSet, basename='release-application-pipeline-config')
router.register(r'application-pipeline-versions', views.ApplicationPipelineVersionViewSet, basename='release-application-pipeline-version')
router.register(r'environment-strategies', views.EnvironmentStrategyViewSet, basename='release-environment-strategy')
router.register(r'cd-exports', views.CDConfigExportViewSet, basename='release-cd-export')

# 发布管理路由
router.register(r'release-records', views.ReleaseRecordViewSet, basename='release-record')
router.register(r'approval-rules', views.ApprovalRuleViewSet, basename='approval-rule')


urlpatterns = [
    path('', include(router.urls)),
    # 应用发布相关 API
    path('application/<int:app_id>/release/', views.trigger_release, name='trigger-release'),
    path('application/<int:app_id>/branches/', views.get_app_branches, name='app-branches'),
    path('application/<int:app_id>/environments/', views.get_app_environments, name='app-environments'),
    path('approval-rules/list/', views.get_approval_rules, name='approval-rules-list'),
    # 发布统计 API
    path('statistics/', views.get_statistics, name='release-statistics'),
    path('statistics/trend/', views.get_trend, name='release-trend'),
    path('statistics/app-rank/', views.get_app_rank, name='release-app-rank'),
]
