# -*- coding: utf-8 -*-
"""
移除 ApprovalRule.is_default 物理列（已被唯一约束方案取代，模型已删除该字段，
但 0024 迁移未显式 RemoveField，导致物理表残留 NOT NULL 列，插入失败）。
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('release', '0024_approval_enhance'),
    ]

    operations = [
        migrations.RunSQL(
            sql=[
                "ALTER TABLE `release_approval_rule` DROP COLUMN `is_default`;",
            ],
            reverse_sql=[
                "ALTER TABLE `release_approval_rule` ADD COLUMN `is_default` tinyint(1) NOT NULL DEFAULT 0;",
            ],
        ),
    ]
