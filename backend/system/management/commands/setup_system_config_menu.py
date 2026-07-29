"""
初始化「系统配置(system_config)」菜单、按钮权限及 Jenkins / Harbor / GitLab 默认配置项。

执行方式:
    python manage.py setup_system_config_menu

说明:
    - 在「系统管理」目录下新增「系统配置」菜单，用于在前端对 system_config 表进行增删改查。
    - 该表同时存放 Jenkins / Harbor / GitLab 等 DevOps 服务的连接信息，
      故脚本会预置这些服务的默认配置行，方便用户在界面上维护。
"""
from django.core.management.base import BaseCommand

from system.models import Config, Menu, MenuMeta


class Command(BaseCommand):
    help = "初始化系统配置(system_config)菜单、按钮权限及 Jenkins/Harbor/GitLab 默认配置"

    def handle(self, *args, **options):
        # 1. 确保 System 目录菜单存在
        system_catalog, _ = Menu.objects.get_or_create(
            name="System",
            type="catalog",
            defaults={
                "status": 1,
                "path": "/system",
                "component": "",
                "auth_code": "",
                "sort": 0,
            },
        )
        if not system_catalog.meta_id:
            meta = MenuMeta.objects.create(
                title="系统管理", icon="ion:settings-outline", sort=0
            )
            system_catalog.meta = meta
            system_catalog.save()

        # 2. 创建 system_config 菜单
        config_meta, _ = MenuMeta.objects.get_or_create(
            title="系统配置",
            defaults={"icon": "carbon:settings", "sort": 0, "hide_in_menu": False},
        )
        config_menu, created = Menu.objects.get_or_create(
            name="SystemConfig",
            defaults={
                "status": 1,
                "type": "menu",
                "path": "/system/config",
                "component": "/system/config/list",
                "auth_code": "system:config:query",
                "pid": system_catalog,
                "meta": config_meta,
                "sort": 50,
            },
        )
        if created:
            self.stdout.write(self.style.SUCCESS("✅ 创建系统配置菜单成功"))
        else:
            self.stdout.write("ℹ️  系统配置菜单已存在")

        # 3. 创建按钮权限
        buttons = [
            ("system:config:query", "查询", 0),
            ("system:config:create", "新增", 1),
            ("system:config:edit", "编辑", 2),
            ("system:config:delete", "删除", 3),
        ]
        for code, title, sort in buttons:
            btn_meta, _ = MenuMeta.objects.get_or_create(
                title=f"配置{title}",
                defaults={"icon": "", "sort": 0, "hide_in_menu": False},
            )
            Menu.objects.get_or_create(
                name=f"SystemConfig{title}",
                defaults={
                    "status": 1,
                    "type": "button",
                    "path": "",
                    "component": "",
                    "auth_code": code,
                    "pid": config_menu,
                    "meta": btn_meta,
                    "sort": sort,
                },
            )
        self.stdout.write(self.style.SUCCESS("✅ 系统配置按钮权限初始化完成"))

        # 4. 初始化 Jenkins / Harbor / GitLab 默认配置项
        default_configs = [
            ("GitLab地址", "gitlab_url", "", 0),
            ("GitLab访问令牌", "gitlab_token", "", 0),
            ("Jenkins地址", "jenkins_url", "", 0),
            ("Jenkins用户名", "jenkins_user", "", 0),
            ("Jenkins密码/Token", "jenkins_password", "", 0),
            ("Harbor地址", "harbor_url", "", 0),
            ("Harbor用户名", "harbor_user", "", 0),
            ("Harbor密码", "harbor_password", "", 0),
            ("Harbor项目", "harbor_project", "", 0),
        ]
        for name, key, value, ctype in default_configs:
            _, created = Config.objects.get_or_create(
                key=key,
                defaults={
                    "name": name,
                    "value": value,
                    "config_type": bool(ctype),
                    "creator": "admin",
                },
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"✅ 创建默认配置: {key}"))
        self.stdout.write(self.style.SUCCESS("🎉 系统配置初始化完成"))
