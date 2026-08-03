# -*- coding: utf-8 -*-
"""
审批机制增强：三级作用域审批规则 + 审批留痕 + ReleaseRecord 多人流转字段
"""
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('release', '0023_alter_application_code_length'),
    ]

    operations = [
        # 1. ApprovalRule 增加作用域与超时通知字段
        migrations.AddField(
            model_name='approvalrule',
            name='project',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='approval_rules',
                to='release.project',
                verbose_name='适用项目（空=全局）',
            ),
        ),
        migrations.AddField(
            model_name='approvalrule',
            name='application',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='approval_rules',
                to='release.application',
                verbose_name='适用应用（空=项目级或全局）',
            ),
        ),
        migrations.AddField(
            model_name='approvalrule',
            name='timeout_hours',
            field=models.IntegerField(blank=True, default=24, null=True, verbose_name='审批超时(小时)'),
        ),
        migrations.AddField(
            model_name='approvalrule',
            name='timeout_action',
            field=models.CharField(
                choices=[('reject', '超时自动拒绝'), ('notify', '超时仅提醒'), ('auto_approve', '超时自动通过')],
                default='reject', max_length=16, verbose_name='超时处理策略',
            ),
        ),
        migrations.AddField(
            model_name='approvalrule',
            name='notify_channels',
            field=models.JSONField(blank=True, default=list, verbose_name='通知渠道'),
        ),
        migrations.AddField(
            model_name='approvalrule',
            name='is_default',
            field=models.BooleanField(default=False, verbose_name='该层级默认规则'),
        ),
        migrations.AddConstraint(
            model_name='approvalrule',
            constraint=models.UniqueConstraint(
                condition=models.Q(is_deleted=False, is_default=True),
                fields=['environment', 'project', 'application'],
                name='uk_default_rule_per_scope',
            ),
        ),

        # 2. ReleaseRecord 增补多人流转字段
        migrations.AddField(
            model_name='releaserecord',
            name='approval_rule',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='releases',
                to='release.approvalrule',
                verbose_name='生效审批规则',
            ),
        ),
        migrations.AddField(
            model_name='releaserecord',
            name='approval_scope',
            field=models.CharField(blank=True, max_length=16, null=True, verbose_name='规则作用域'),
        ),
        migrations.AddField(
            model_name='releaserecord',
            name='approved_count',
            field=models.IntegerField(default=0, verbose_name='已通过数'),
        ),
        migrations.AddField(
            model_name='releaserecord',
            name='required_count',
            field=models.IntegerField(default=1, verbose_name='需通过数'),
        ),
        migrations.AddField(
            model_name='releaserecord',
            name='current_approver_ids',
            field=models.JSONField(blank=True, default=list, verbose_name='当前待审批人ID'),
        ),
        migrations.AddField(
            model_name='releaserecord',
            name='approval_deadline',
            field=models.DateTimeField(blank=True, null=True, verbose_name='审批截止时间'),
        ),

        # 3. 新建 ApprovalRecord 审批留痕表
        migrations.CreateModel(
            name='ApprovalRecord',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('remark', models.CharField(blank=True, max_length=256, null=True, verbose_name='备注')),
                ('creator', models.CharField(blank=True, max_length=64, null=True, verbose_name='创建人')),
                ('modifier', models.CharField(blank=True, max_length=64, null=True, verbose_name='修改人')),
                ('create_time', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('update_time', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('is_deleted', models.BooleanField(default=False, verbose_name='是否删除')),
                ('approver_id', models.IntegerField(verbose_name='审批人ID')),
                ('approver_name', models.CharField(max_length=64, verbose_name='审批人姓名')),
                ('order', models.IntegerField(default=0, verbose_name='审批顺序')),
                ('action', models.CharField(
                    choices=[('approve', '通过'), ('reject', '拒绝'), ('transfer', '转交'), ('add_sign', '加签')],
                    max_length=16, verbose_name='操作类型',
                )),
                ('comment', models.TextField(blank=True, verbose_name='审批意见')),
                ('acted_at', models.DateTimeField(verbose_name='操作时间')),
                ('delegate_to_id', models.IntegerField(blank=True, null=True, verbose_name='转交目标人ID')),
                ('delegate_to_name', models.CharField(blank=True, max_length=64, verbose_name='转交目标人姓名')),
                ('release', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='approval_records',
                    to='release.releaserecord', verbose_name='关联发布记录',
                )),
                ('rule', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='records',
                    to='release.approvalrule', verbose_name='关联审批规则',
                )),
            ],
            options={
                'verbose_name': '审批操作记录',
                'verbose_name_plural': '审批操作记录',
                'db_table': 'release_approval_record',
                'ordering': ['order', 'acted_at'],
            },
        ),
    ]
