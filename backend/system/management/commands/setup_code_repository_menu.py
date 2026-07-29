# -*- coding: utf-8 -*-
"""
添加代码仓库菜单权限的管理命令

使用方法:
    python manage.py setup_code_repository_menu
"""
from django.core.management.base import BaseCommand
from system.models import Menu, MenuMeta


class Command(BaseCommand):
    help = '添加代码仓库菜单和按钮权限'

    def handle(self, *args, **options):
        # 查找发布管理目录菜单
        release_catalog = Menu.objects.filter(
            name='发布管理',
            type='catalog',
            path='/release'
        ).first()

        if not release_catalog:
            self.stdout.write(self.style.WARNING('未找到发布管理目录菜单'))
            return

        # 查找代码仓库菜单
        repo_menu = Menu.objects.filter(
            path='/release/code-repository',
            type='menu'
        ).first()

        if not repo_menu:
            # 创建代码仓库菜单
            repo_meta, created = MenuMeta.objects.get_or_create(
                title='代码仓库',
                defaults={
                    'icon': 'mdi:source-repository',
                    'sort': 0,
                }
            )
            repo_menu = Menu.objects.create(
                name='CodeRepository',
                path='/release/code-repository',
                status=1,
                type='menu',
                component='/release/codeRepository/index',
                auth_code='release:code-repository:view',
                pid=release_catalog,
                meta=repo_meta,
                sort=0
            )
            self.stdout.write(self.style.SUCCESS(f'创建代码仓库菜单: ID={repo_menu.id}'))
        else:
            self.stdout.write(f'代码仓库菜单已存在: ID={repo_menu.id}')

        # 定义按钮权限列表
        buttons = [
            {'name': 'CodeRepositoryCreate', 'title': '创建仓库', 'auth_code': 'release:code-repository:create', 'sort': 1},
            {'name': 'CodeRepositoryUpdate', 'title': '编辑仓库', 'auth_code': 'release:code-repository:update', 'sort': 2},
            {'name': 'CodeRepositoryDelete', 'title': '删除仓库', 'auth_code': 'release:code-repository:delete', 'sort': 3},
        ]

        # 创建按钮权限
        for btn in buttons:
            btn_meta, created = MenuMeta.objects.get_or_create(
                title=btn['title'],
                defaults={
                    'icon': '',
                    'sort': btn['sort'],
                }
            )
            btn_menu, created = Menu.objects.get_or_create(
                name=btn['name'],
                pid=repo_menu,
                defaults={
                    'status': 1,
                    'type': 'button',
                    'path': '',
                    'component': '',
                    'auth_code': btn['auth_code'],
                    'meta': btn_meta,
                    'sort': btn['sort']
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'创建按钮权限: {btn["title"]} ({btn["auth_code"]})'))
            else:
                self.stdout.write(f'按钮权限已存在: {btn["title"]}')

        self.stdout.write(self.style.SUCCESS('代码仓库菜单配置完成！'))
        self.stdout.write(self.style.WARNING('请在角色管理中分配相应权限后生效'))
