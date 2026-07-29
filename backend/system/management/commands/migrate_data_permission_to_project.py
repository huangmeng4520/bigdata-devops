# -*- coding: utf-8 -*-
"""
将历史以 application 为范围单位的数据权限规则，迁移为 project 范围单位。

背景：数据权限统一以「项目」为根节点，应用/模块/代码库/配置包等按 project 级联隔离。
早期授权页以 application 为单位写入了 scope_type='application' 的规则，本命令将其
转换为 scope_type='project'（scope_id = 应用所属项目 id），并去重。

运行：python manage.py migrate_data_permission_to_project
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from system.models import DataPermissionRule
from release.models import Application


class Command(BaseCommand):
    help = '将 scope_type=application 的数据权限规则迁移为 scope_type=project'

    def handle(self, *args, **options):
        legacy_rules = DataPermissionRule.objects.filter(
            scope_type='application', is_deleted=False
        )
        total = legacy_rules.count()
        if total == 0:
            self.stdout.write(self.style.SUCCESS('没有需要迁移的 application 级规则。'))
            return

        converted = 0
        skipped = 0
        with transaction.atomic():
            for rule in legacy_rules:
                app = Application.objects.filter(id=rule.scope_id).first()
                if not app or not app.project_id:
                    skipped += 1
                    continue
                project_id = app.project_id
                # 唯一约束为 (scope_type, scope_id, user)，不含 level，
                # 因此以三字段为准做幂等写入，避免重复键冲突。
                _, created = DataPermissionRule.objects.get_or_create(
                    scope_type='project',
                    scope_id=project_id,
                    user=rule.user,
                    defaults={'level': rule.level, 'creator': rule.creator},
                )
                if created:
                    converted += 1
                else:
                    skipped += 1
            # 迁移完成后清理历史 application 规则
            deleted, _ = DataPermissionRule.objects.filter(
                scope_type='application', is_deleted=False
            ).delete()

        self.stdout.write(
            self.style.SUCCESS(
                f'迁移完成：转换 {converted} 条，跳过 {skipped} 条，'
                f'删除 {deleted} 条历史 application 规则（共 {total} 条）。'
            )
        )
