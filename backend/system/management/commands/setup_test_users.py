# -*- coding: utf-8 -*-
"""
创建三个角色测试用户，用于验证 release 模块 RBAC + 数据权限：

- ops_test   / Test@123456  运维（数据范围 all，全部菜单+按钮）
- lead_test  / Test@123456  研发技术负责人（数据范围 all，含项目权限分配页）
- dev_test   / Test@123456  研发（数据范围 custom，仅可见被分配的项目及其下应用/模块/代码）

同时把前 2 个项目通过 DataPermissionRule 分配给 dev_test，方便验证项目级数据隔离与级联。

用法:
    python manage.py setup_test_users
    python manage.py setup_test_users --password 自定义密码
"""
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand, CommandError

from system.models import User, Role, DataPermissionRule, CommonStatus

TEST_USERS = [
    ('ops_test', '测试-运维', 'ops'),
    ('lead_test', '测试-技术负责人', 'dev_lead'),
    ('dev_test', '测试-研发', 'developer'),
]

DEFAULT_PASSWORD = 'Test@123456'


class Command(BaseCommand):
    help = '创建 ops/dev_lead/developer 三个测试用户并为研发分配示例项目数据权限'

    def add_arguments(self, parser):
        parser.add_argument('--password', default=DEFAULT_PASSWORD, help='测试用户密码')

    def handle(self, *args, **options):
        password = options['password']

        roles = {r.code: r for r in Role.objects.filter(code__in=[c for _, _, c in TEST_USERS])}
        missing = [c for _, _, c in TEST_USERS if c not in roles]
        if missing:
            raise CommandError(
                f'角色不存在: {missing}，请先执行 python manage.py setup_release_roles'
            )

        for username, nickname, role_code in TEST_USERS:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'nickname': nickname,
                    'password': make_password(password),
                    'status': CommonStatus.ENABLED,
                    'is_active': True,
                    'creator': 'system',
                },
            )
            if not created:
                user.nickname = nickname
                user.password = make_password(password)
                user.is_active = True
                user.status = CommonStatus.ENABLED
                user.save(update_fields=['nickname', 'password', 'is_active', 'status'])
            user.role.set([roles[role_code]])
            self.stdout.write(
                f'{"创建" if created else "更新"}用户 {username}（{nickname}）'
                f' -> 角色 {roles[role_code].name}'
            )

        # 给研发用户分配前 2 个项目的数据权限（级联可见其下应用/模块/代码）
        from release.models import Project

        dev_user = User.objects.get(username='dev_test')
        projects = list(Project.objects.filter(is_deleted=False).order_by('id')[:2])
        if projects:
            DataPermissionRule.objects.filter(scope_type='project', user=dev_user).delete()
            for project in projects:
                DataPermissionRule.objects.create(
                    scope_type='project',
                    scope_id=project.id,
                    user=dev_user,
                    creator='system',
                )
            self.stdout.write(
                f'已给 dev_test 分配项目数据权限（级联可见其下应用/模块/代码）: '
                f'{[f"{p.id}:{getattr(p, "name", p.id)}" for p in projects]}'
            )
        else:
            self.stdout.write(self.style.WARNING('暂无项目数据，跳过 dev_test 数据权限分配'))

        self.stdout.write(self.style.SUCCESS(
            f'\n完成！测试账号（密码均为 {password}）：\n'
            '  - ops_test   运维：全部菜单/按钮，全部数据\n'
            '  - lead_test  技术负责人：release 全功能 + 应用权限分配页，全部数据\n'
            '  - dev_test   研发：仅 release 基础操作，仅看到被分配的项目及其下应用/模块/代码'
        ))
