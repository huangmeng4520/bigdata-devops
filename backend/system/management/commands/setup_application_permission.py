# -*- coding: utf-8 -*-
"""
添加应用管理按钮权限的管理命令

使用方法:
    python manage.py setup_application_permission
"""
from django.core.management.base import BaseCommand
from django.db import IntegrityError
from system.models import Menu, MenuMeta


class Command(BaseCommand):
    help = '添加应用管理按钮权限'

    def handle(self, *args, **options):
        # 查找应用管理菜单 (父目录 ID 101)
        app_menu = Menu.objects.filter(
            name='应用管理',
            path='/release/application',
            type='menu'
        ).first()

        if not app_menu:
            self.stdout.write(self.style.WARNING('未找到应用管理菜单，请先创建菜单'))
            return

        self.stdout.write(f'应用管理菜单: ID={app_menu.id}, pid={app_menu.pid_id}')

        # 定义按钮权限列表
        buttons = [
            {'name': 'ApplicationCreate', 'title': '创建应用', 'auth_code': 'release:application:create', 'sort': 1},
            {'name': 'ApplicationUpdate', 'title': '编辑应用', 'auth_code': 'release:application:update', 'sort': 2},
            {'name': 'ApplicationDelete', 'title': '删除应用', 'auth_code': 'release:application:delete', 'sort': 3},
            {'name': 'ApplicationRelease', 'title': '发布应用', 'auth_code': 'release:application:release', 'sort': 4},
            {'name': 'ApplicationSyncJenkins', 'title': '同步CI/CD', 'auth_code': 'release:application:sync-jenkins', 'sort': 5},
            {'name': 'ApplicationSyncGitlab', 'title': '同步GitLab', 'auth_code': 'release:application:sync-gitlab', 'sort': 6},
            {'name': 'ApplicationSyncJenkinsResource', 'title': '同步Jenkins资源', 'auth_code': 'release:application:sync-jenkins-resource', 'sort': 7},
            {'name': 'ApplicationSyncHarbor', 'title': '同步Harbor', 'auth_code': 'release:application:sync-harbor', 'sort': 8},
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
            try:
                btn_menu, created = Menu.objects.get_or_create(
                    name=btn['name'],
                    pid=app_menu,
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
            except IntegrityError:
                btn_menu = Menu.objects.filter(name=btn['name'], pid=app_menu).first()
                if btn_menu:
                    self.stdout.write(f'按钮权限已存在: {btn["title"]}')
                else:
                    self.stdout.write(self.style.WARNING(f'无法创建按钮权限: {btn["title"]}'))

        self.stdout.write(self.style.SUCCESS('按钮权限配置完成！'))
        self.stdout.write(self.style.WARNING('请在角色管理中分配相应权限后生效'))
