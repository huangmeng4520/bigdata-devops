# -*- coding: utf-8 -*-
from django.apps import AppConfig


class ReleaseConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'release'
    verbose_name = '发布管理'

    def ready(self):
        # 注册信号，保证应用级同步状态随环境级配置自动聚合
        from . import signals  # noqa: F401
