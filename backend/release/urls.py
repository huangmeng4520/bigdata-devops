# -*- coding: utf-8 -*-
"""
发布管理路由配置
"""
from django.urls import include, path
from rest_framework import routers

from . import views

router = routers.DefaultRouter()
router.register(r'project', views.ProjectViewSet, basename='release-project')
router.register(r'module', views.ModuleViewSet, basename='release-module')
router.register(r'application', views.ApplicationViewSet, basename='release-application')
router.register(r'config-package', views.ConfigPackageViewSet, basename='release-config-package')
router.register(r'sync-log', views.SyncLogViewSet, basename='release-sync-log')
router.register(r'template', views.TemplateViewSet, basename='release-template')

urlpatterns = [
    path('', include(router.urls)),
]
