# -*- coding: utf-8 -*-
"""
添加应用的 CI/CD 模板关联字段
"""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('release', '0003_add_jenkins_sync_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='application',
            name='ci_template',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='ci_applications',
                to='release.pipelinetemplate',
                verbose_name='CI 流水线模板'
            ),
        ),
        migrations.AddField(
            model_name='application',
            name='ci_variables',
            field=models.JSONField(blank=True, default=dict, verbose_name='CI 变量配置'),
        ),
        migrations.AddField(
            model_name='application',
            name='cd_template',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='cd_applications',
                to='release.pipelinetemplate',
                verbose_name='CD 流水线模板'
            ),
        ),
        migrations.AddField(
            model_name='application',
            name='cd_variables',
            field=models.JSONField(blank=True, default=dict, verbose_name='CD 变量配置'),
        ),
        migrations.AddField(
            model_name='application',
            name='jenkins_sync_status',
            field=models.IntegerField(
                choices=[(0, '待同步'), (1, '同步中'), (2, '已同步'), (3, '同步失败')],
                default=0,
                verbose_name='Jenkins 同步状态'
            ),
        ),
        migrations.AddField(
            model_name='application',
            name='jenkins_sync_time',
            field=models.DateTimeField(blank=True, null=True, verbose_name='最后同步时间'),
        ),
        migrations.AddField(
            model_name='application',
            name='jenkins_sync_message',
            field=models.CharField(blank=True, max_length=512, null=True, verbose_name='同步消息'),
        ),
    ]
