# -*- coding: utf-8 -*-
"""
初始化发布管理 GitLab 相关配置项的管理命令。

为 system_config 表补充 gitlab_external_url 配置项（前端浏览器展示/跳转用
外网地址）。若已存在则不覆盖，仅打印提示。

使用方法:
    python manage.py setup_release_config
"""
from django.core.management.base import BaseCommand

from system.models import Config


class Command(BaseCommand):
    help = '初始化发布管理 GitLab 相关配置项（gitlab_external_url 等）'

    # 需确保存在的配置项：key、默认值、是否系统内置、参数名称、备注
    CONFIG_ITEMS = [
        {
            'key': 'gitlab_external_url',
            'name': 'GitLab外网地址',
            'value': '',
            'config_type': False,
            'remark': '前端浏览器展示/跳转用的 GitLab 外网地址；为空时回退到 gitlab_url。'
                      '示例：https://gitlab.example.com',
        },
    ]

    def handle(self, *args, **options):
        created_count = 0
        skipped_count = 0

        for item in self.CONFIG_ITEMS:
            obj, created = Config.objects.get_or_create(
                key=item['key'],
                defaults={
                    'name': item['name'],
                    'value': item['value'],
                    'config_type': item['config_type'],
                    'remark': item.get('remark', ''),
                },
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(
                    f'已新增配置项: {item["key"]} ({item["name"]})'
                ))
            else:
                skipped_count += 1
                self.stdout.write(f'配置项已存在，跳过: {item["key"]} (当前值: {obj.value or "(空)"})')

        self.stdout.write(self.style.SUCCESS(
            f'\n完成：新增 {created_count} 项，跳过 {skipped_count} 项'
        ))
        self.stdout.write(
            '\n请到「系统管理 -> 参数配置」中为 gitlab_external_url 填写外网地址。'
            '若 GitLab 内外网地址相同，可留空（自动回退到 gitlab_url）。'
        )
