# -*- coding: utf-8 -*-
"""
添加发布管理相关权限的管理命令

使用方法:
    python manage.py setup_release_permissions
"""
from django.core.management.base import BaseCommand
from django.db import IntegrityError
from system.models import Menu, MenuMeta


class Command(BaseCommand):
    help = '添加发布管理相关权限'

    def handle(self, *args, **options):
        menus_buttons = [
            {
                'menu_path': '/release/project',
                'menu_name': 'Project',
                'buttons': [
                    {'name': 'ProjectCreate', 'title': '新增项目', 'auth_code': 'release:project:create'},
                    {'name': 'ProjectEdit', 'title': '编辑项目', 'auth_code': 'release:project:edit'},
                    {'name': 'ProjectDelete', 'title': '删除项目', 'auth_code': 'release:project:delete'},
                    {'name': 'ProjectCreateModule', 'title': '创建模块', 'auth_code': 'release:module:create'},
                    {'name': 'ProjectSyncGitlab', 'title': '同步GitLab(项目)', 'auth_code': 'release:project:sync-gitlab'},
                ]
            },
            {
                'menu_path': '/release/module',
                'menu_name': 'Module',
                'buttons': [
                    {'name': 'ModuleEdit', 'title': '编辑模块', 'auth_code': 'release:module:edit'},
                    {'name': 'ModuleDelete', 'title': '删除模块', 'auth_code': 'release:module:delete'},
                    {'name': 'ModuleSyncGitlab', 'title': '同步GitLab(模块)', 'auth_code': 'release:module:sync-gitlab'},
                ]
            },
            {
                'menu_path': '/release/application',
                'menu_name': 'Application',
                'buttons': [
                    {'name': 'ApplicationCreate', 'title': '新增应用', 'auth_code': 'release:application:create'},
                    {'name': 'ApplicationEdit', 'title': '编辑应用', 'auth_code': 'release:application:edit'},
                    {'name': 'ApplicationUpdate', 'title': '编辑应用(前端)', 'auth_code': 'release:application:update'},
                    {'name': 'ApplicationDelete', 'title': '删除应用', 'auth_code': 'release:application:delete'},
                    {'name': 'ConfigPackageCreate', 'title': '新增配置包', 'auth_code': 'release:config_package:create'},
                    {'name': 'ConfigPackageEdit', 'title': '编辑配置包', 'auth_code': 'release:config_package:edit'},
                    {'name': 'ConfigPackageDelete', 'title': '删除配置包', 'auth_code': 'release:config_package:delete'},
                    {'name': 'AppPipelineConfigCreate', 'title': '新增流水线配置', 'auth_code': 'release:application_pipeline_config:create'},
                    {'name': 'AppPipelineConfigEdit', 'title': '编辑流水线配置', 'auth_code': 'release:application_pipeline_config:edit'},
                    {'name': 'AppPipelineConfigDelete', 'title': '删除流水线配置', 'auth_code': 'release:application_pipeline_config:delete'},
                ]
            },
            {
                'menu_path': '/release/code-repository',
                'menu_name': 'CodeRepository',
                'buttons': [
                    {'name': 'CodeRepositoryCreate', 'title': '新增代码仓库', 'auth_code': 'release:code_repository:create'},
                    {'name': 'CodeRepositoryEdit', 'title': '编辑代码仓库', 'auth_code': 'release:code_repository:edit'},
                    {'name': 'CodeRepositoryUpdate', 'title': '编辑代码仓库(前端)', 'auth_code': 'release:code_repository:update'},
                    {'name': 'CodeRepositoryDelete', 'title': '删除代码仓库', 'auth_code': 'release:code_repository:delete'},
                ]
            },
            {
                'menu_path': '/release/pipeline-template',
                'menu_name': 'PipelineTemplate',
                'buttons': [
                    {'name': 'PipelineTemplateCreate', 'title': '新增流水线模板', 'auth_code': 'release:pipeline_template:create'},
                    {'name': 'PipelineTemplateEdit', 'title': '编辑流水线模板', 'auth_code': 'release:pipeline_template:edit'},
                    {'name': 'PipelineTemplateDelete', 'title': '删除流水线模板', 'auth_code': 'release:pipeline_template:delete'},
                    {'name': 'PipelineTemplateVersionCreate', 'title': '新增模板版本', 'auth_code': 'release:pipeline_template_version:create'},
                    {'name': 'PipelineTemplateVersionEdit', 'title': '编辑模板版本', 'auth_code': 'release:pipeline_template_version:edit'},
                    {'name': 'PipelineTemplateVersionDelete', 'title': '删除模板版本', 'auth_code': 'release:pipeline_template_version:delete'},
                ]
            },
            {
                'menu_path': '/release/environment-strategy',
                'menu_name': 'EnvironmentStrategy',
                'buttons': [
                    {'name': 'EnvironmentStrategyCreate', 'title': '新增环境策略', 'auth_code': 'release:environment_strategy:create'},
                    {'name': 'EnvironmentStrategyEdit', 'title': '编辑环境策略', 'auth_code': 'release:environment_strategy:edit'},
                    {'name': 'EnvironmentStrategyDelete', 'title': '删除环境策略', 'auth_code': 'release:environment_strategy:delete'},
                ]
            },
            {
                'menu_path': '/release/record',
                'menu_name': 'ReleaseRecord',
                'buttons': [
                    {'name': 'ReleaseRecordCreate', 'title': '新增发布记录', 'auth_code': 'release:release_record:create'},
                    {'name': 'ReleaseRecordEdit', 'title': '编辑发布记录', 'auth_code': 'release:release_record:edit'},
                    {'name': 'ReleaseRecordDelete', 'title': '删除发布记录', 'auth_code': 'release:release_record:delete'},
                    {'name': 'ReleaseRecordTrigger', 'title': '触发发布', 'auth_code': 'release:release_record:trigger'},
                    {'name': 'ReleaseRecordCancel', 'title': '取消发布', 'auth_code': 'release:release_record:cancel'},
                    {'name': 'ReleaseRecordApprove', 'title': '审批通过', 'auth_code': 'release:release_record:approve'},
                    {'name': 'ReleaseRecordReject', 'title': '审批拒绝', 'auth_code': 'release:release_record:reject'},
                    {'name': 'ReleaseRecordRetry', 'title': '重试发布', 'auth_code': 'release:release_record:retry'},
                    {'name': 'ReleaseRecordAIAnalysis', 'title': 'AI分析', 'auth_code': 'release:release_record:ai_analysis'},
                ]
        },
        {
            # 审批规则按钮权限挂在审批规则菜单下（与 setup_approval_menu.py 一致）
            'menu_path': '/release/approval-rule',
            'menu_name': 'ApprovalRule',
            'buttons': [
                {'name': 'ApprovalRuleCreate', 'title': '新增审批规则', 'auth_code': 'release:approval_rule:create'},
                {'name': 'ApprovalRuleEdit', 'title': '编辑审批规则', 'auth_code': 'release:approval_rule:edit'},
                {'name': 'ApprovalRuleDelete', 'title': '删除审批规则', 'auth_code': 'release:approval_rule:delete'},
            ]
        },
    ]

        for menu_config in menus_buttons:
            menu = Menu.objects.filter(
                path=menu_config['menu_path'],
                type='menu'
            ).first()

            if not menu:
                self.stdout.write(self.style.WARNING(f'未找到菜单: {menu_config["menu_path"]}'))
                continue

            self.stdout.write(f'处理菜单: {menu_config["menu_path"]}')

            for btn in menu_config['buttons']:
                btn_meta, created = MenuMeta.objects.get_or_create(
                    title=btn['title'],
                    defaults={
                        'icon': '',
                        'sort': 99,
                    }
                )
                try:
                    btn_menu, created = Menu.objects.get_or_create(
                        name=btn['name'],
                        pid=menu,
                        defaults={
                            'status': 1,
                            'type': 'button',
                            'path': '',
                            'component': '',
                            'auth_code': btn['auth_code'],
                            'meta': btn_meta,
                            'sort': 99
                        }
                    )
                    if created:
                        self.stdout.write(self.style.SUCCESS(f'  创建按钮: {btn["title"]} ({btn["auth_code"]})'))
                    else:
                        self.stdout.write(f'  按钮已存在: {btn["title"]}')
                except IntegrityError:
                    btn_menu = Menu.objects.filter(name=btn['name'], pid=menu).first()
                    if btn_menu:
                        self.stdout.write(f'  按钮已存在: {btn["title"]}')
                    else:
                        self.stdout.write(self.style.WARNING(f'  无法创建按钮: {btn["title"]}'))

        self.stdout.write(self.style.SUCCESS('权限配置完成！'))
        self.stdout.write(self.style.WARNING('请在角色管理中分配相应权限后生效'))
