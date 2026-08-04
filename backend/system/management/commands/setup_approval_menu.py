# -*- coding: utf-8 -*-
"""
添加审批规则菜单的管理命令

使用方法:
    python manage.py setup_approval_menu
"""
from django.core.management.base import BaseCommand
from system.models import Menu, MenuMeta


class Command(BaseCommand):
    help = '添加审批规则菜单（component 指向前端 approvalRule/index.vue）'

    def handle(self, *args, **options):
        # 查找发布管理目录菜单
        release_catalog = Menu.objects.filter(
            name='Release',
            type='catalog',
            path='/release'
        ).first()

        if not release_catalog:
            self.stdout.write(self.style.ERROR('未找到发布管理目录菜单，请先执行 setup_release_menu'))
            return

        # 创建审批规则菜单
        meta, _ = MenuMeta.objects.get_or_create(
            title='审批规则',
            defaults={
                'icon': 'mdi:clipboard-check-outline',
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

        # 关键：component 字段必须与前端 pageMap 的 key 匹配
        # pageMap = import.meta.glob('../views/**/*.vue')
        # key 形如 ../views/release/approvalRule/index.vue
        # vben 框架会自动用 component 字段去匹配，格式为 /release/approvalRule/index
        menu, created = Menu.objects.update_or_create(
            name='ReleaseApprovalRule',
            path='/release/approval-rule',
            defaults={
                'status': 1,
                'type': 'menu',
                'component': '/release/approvalRule/index',
                'auth_code': 'release:approval_rule:view',
                'pid': release_catalog,
                'meta': meta,
                'sort': 7,  # 在流水线模板之后、发布记录之前
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f'创建审批规则菜单: ID={menu.id}'))
        else:
            self.stdout.write(self.style.SUCCESS(f'更新审批规则菜单(component 已修正): ID={menu.id}'))

        # 同步创建/更新审批规则按钮权限
        buttons = [
            {'name': 'ApprovalRuleCreate', 'title': '新增审批规则', 'auth_code': 'release:approval_rule:create'},
            {'name': 'ApprovalRuleEdit', 'title': '编辑审批规则', 'auth_code': 'release:approval_rule:edit'},
            {'name': 'ApprovalRuleDelete', 'title': '删除审批规则', 'auth_code': 'release:approval_rule:delete'},
        ]

        for btn in buttons:
            btn_meta, _ = MenuMeta.objects.get_or_create(
                title=btn['title'],
                defaults={'icon': '', 'sort': 99}
            )
            Menu.objects.update_or_create(
                name=btn['name'],
                pid=menu,
                defaults={
                    'status': 1,
                    'type': 'button',
                    'path': '',
                    'component': '',
                    'auth_code': btn['auth_code'],
                    'meta': btn_meta,
                    'sort': 99,
                }
            )
            self.stdout.write(f'  同步按钮权限: {btn["title"]}')

        self.stdout.write(self.style.SUCCESS('审批规则菜单配置完成！'))
        self.stdout.write(self.style.WARNING('请确保角色已分配 release:approval_rule:* 权限'))
