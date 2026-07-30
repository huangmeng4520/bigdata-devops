# -*- coding: utf-8 -*-
"""发布管理信号：保持应用级同步状态与环境级配置一致"""
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import ApplicationPipelineConfig


@receiver(post_save, sender=ApplicationPipelineConfig)
def pipeline_config_post_save(sender, instance, **kwargs):
    """流水线配置保存（状态/配置变更）后，重新聚合所属应用的 Jenkins 同步状态"""
    application = instance.application
    if application and application.pk:
        try:
            application.refresh_jenkins_sync_status()
        except Exception:
            # 信号内异常不应影响主流程
            pass
