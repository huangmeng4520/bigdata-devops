# -*- coding: utf-8 -*-
"""
添加发布记录和发布统计菜单的管理命令

使用方法:
    python manage.py setup_release_menu
"""
from django.core.management.base import BaseCommand
from system.models import Menu, MenuMeta


class Command(BaseCommand):
    help = '添加发布记录和发布统计菜单'

    def handle(self, *args, **options):
        # 查找发布管理目录菜单
        release_catalog = Menu.objects.filter(
            name='Release',
            type='catalog',
            path='/release'
        ).first()

        if not release_catalog:
            self.stdout.write(self.style.WARNING('未找到发布管理目录菜单，请先在后台创建'))
            # 创建发布管理目录
            meta, created = MenuMeta.objects.get_or_create(
                title='发布管理',
                defaults={
                    'icon': 'mdi:rocket-launch',
                    'sort': 0,
                    'affix_tab': False,
                    'badge': '',
                    'badge_type': '',
                    'badge_variants': '',
                    'iframe_src': '',
                    'link': '',
                    'hide_children_in_menu': False,
                    'hide_in_menu': False,
                }
            )
            release_catalog = Menu.objects.create(
                name='Release',
                status=1,
                type='catalog',
                path='/release',
                component='',
                auth_code='',
                meta=meta,
                sort=9998
            )
            self.stdout.write(self.style.SUCCESS(f'创建发布管理目录菜单: ID={release_catalog.id}'))

        # 添加发布记录菜单
        record_meta, created = MenuMeta.objects.get_or_create(
            title='发布记录',
            defaults={
                'icon': 'mdi:history',
                'sort': 0,
                'affix_tab': False,
                'badge': '',
                'badge_type': '',
                'badge_variants': '',
                'iframe_src': '',
                'link': '',
                'hide_children_in_menu': False,
                'hide_in_menu': False,
            }
        )

        record_menu, created = Menu.objects.get_or_create(
            name='ReleaseRecord',
            path='/release/record',
            defaults={
                'status': 1,
                'type': 'menu',
                'component': '/release/record/index',
                'auth_code': 'release:record:view',
                'pid': release_catalog,
                'meta': record_meta,
                'sort': 7
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f'创建发布记录菜单: ID={record_menu.id}'))
        else:
            self.stdout.write(f'发布记录菜单已存在: ID={record_menu.id}')

        # 添加发布统计菜单
        stats_meta, created = MenuMeta.objects.get_or_create(
            title='发布统计',
            defaults={
                'icon': 'mdi:chart-bar',
                'sort': 0,
                'affix_tab': False,
                'badge': '',
                'badge_type': '',
                'badge_variants': '',
                'iframe_src': '',
                'link': '',
                'hide_children_in_menu': False,
                'hide_in_menu': False,
            }
        )

        stats_menu, created = Menu.objects.get_or_create(
            name='ReleaseStatistics',
            path='/release/statistics',
            defaults={
                'status': 1,
                'type': 'menu',
                'component': '/release/statistics/index',
                'auth_code': 'release:statistics:view',
                'pid': release_catalog,
                'meta': stats_meta,
                'sort': 8
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f'创建发布统计菜单: ID={stats_menu.id}'))
        else:
            self.stdout.write(f'发布统计菜单已存在: ID={stats_menu.id}')

        self.stdout.write(self.style.SUCCESS('菜单配置完成！'))
