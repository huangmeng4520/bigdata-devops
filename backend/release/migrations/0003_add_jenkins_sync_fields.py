# -*- coding: utf-8 -*-
"""
添加 Jenkins 同步状态字段到 ApplicationPipelineConfig
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('release', '0002_cicd_template_system'),
    ]

    operations = [
        migrations.AddField(
            model_name='applicationpipelineconfig',
            name='jenkins_sync_status',
            field=models.IntegerField(
                choices=[(0, '待同步'), (1, '同步中'), (2, '已同步'), (3, '同步失败')],
                default=0,
                verbose_name='Jenkins 同步状态'
            ),
        ),
        migrations.AddField(
            model_name='applicationpipelineconfig',
            name='jenkins_sync_time',
            field=models.DateTimeField(blank=True, null=True, verbose_name='最后同步时间'),
        ),
        migrations.AddField(
            model_name='applicationpipelineconfig',
            name='jenkins_sync_message',
            field=models.CharField(blank=True, max_length=512, null=True, verbose_name='同步消息'),
        ),
        migrations.AddField(
            model_name='applicationpipelineconfig',
            name='jenkins_job_name',
            field=models.CharField(blank=True, max_length=256, null=True, verbose_name='Jenkins Job 名称'),
        ),
    ]
