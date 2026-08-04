# -*- coding: utf-8 -*-
"""
初始化发布中心（release）权限角色与权限矩阵。

角色（完全可配置，仅初始预置三个）：
- ops          运维：数据范围=全部，拥有所有模块全部权限（字面“所有权限”）
- dev_lead     研发技术负责人：数据范围=全部，拥有 项目/模块/仓库/应用/流水线模板/配置包 全量维护 + 发布触发
- developer    研发：数据范围=自定义（按分配应用），等同应用维护权限（其被分配应用上的增删改查 + 触发发布）

权限码规范统一为：release:<model>:<query|create|edit|delete>（与框架推导及系统模块保持一致）。
模型名使用连字符（如 code-repository），与前端菜单管理创建的按钮码保持一致。

幂等：重复执行安全，先清空这三个角色的权限再按矩阵重新分配。
"""
from django.core.management.base import BaseCommand
from django.db.models import Q, Count

from system.models import (
    Role, Menu, MenuMeta, RolePermission, MenuType, CommonStatus
)

# release 模块业务模型（下划线，与前端按钮码一致：CodeRepository -> code_repository）
RELEASE_MODELS = [
    'project', 'module', 'code_repository', 'application', 'config_package',
    'application_pipeline_config', 'pipeline_template',
    'release_record', 'sync_log', 'approval_rule',
]

STANDARD = ['query', 'create', 'edit', 'delete']

# 各模型的自定义动作（对应视图集中的 @action）
CUSTOM = {
    'application': ['release', 'sync-jenkins', 'sync-gitlab',
                    'sync-harbor'],
    'code_repository': ['import', 'sync-gitlab'],
    'project': ['sync-gitlab'],
    'module': ['import', 'sync-gitlab'],
    'release_record': ['trigger', 'cancel', 'retry'],
}
# 仅运维/技术负责人拥有的审批类动作
APPROVE_CUSTOM = {
    'release_record': ['approve', 'reject'],
}

# 模型 -> 前端菜单 path（用于把按钮挂到对应菜单下，便于展示）
PATH_MAP = {
    'project': '/release/project',
    'module': '/release/module',
    'code_repository': '/release/code-repository',
    'application': '/release/application',
    'config_package': '/release/config-package',
    'application_pipeline_config': '/release/pipeline',
    'pipeline_template': '/release/pipeline-template',
    'release_record': '/release/record',
    'sync_log': '/release/sync-log',
    'approval_rule': '/release/approval-rule',
}

STANDARD_TITLE = {'query': '查询', 'create': '新增', 'edit': '编辑', 'delete': '删除'}

# edit / update 为同一语义的不同写法（前端有的用 update），统一兼容
EDIT_ALT = {'edit': 'update', 'update': 'edit'}


def ensure_role(code, name, data_scope, remark):
    role, created = Role.objects.get_or_create(
        code=code,
        defaults={
            'name': name,
            'data_scope': data_scope,
            'status': CommonStatus.ENABLED,
            'sort': 1,
            'remark': remark,
            'creator': 'system',
        },
    )
    if not created:
        role.data_scope = data_scope
        role.save(update_fields=['data_scope'])
    return role


def variants_of(auth_code):
    """生成下划线/连字符两种写法，兼容历史不一致的按钮码。"""
    vs = {auth_code}
    if '_' in auth_code:
        vs.add(auth_code.replace('_', '-'))
    if '-' in auth_code:
        vs.add(auth_code.replace('-', '_'))
    return list(vs)


def ensure_button(auth_code, title, parent_path=None):
    parent = None
    if parent_path:
        parent = Menu.objects.filter(path=parent_path, type=MenuType.MENU).first()
    # 兼容下划线/连字符两种写法，复用同一按钮，并归一化为规范连字符码，避免重复
    menu = Menu.objects.filter(
        auth_code__in=variants_of(auth_code), type=MenuType.BUTTON
    ).first()
    if menu:
        if menu.auth_code != auth_code:
            menu.auth_code = auth_code  # 归一化为规范连字符码
            menu.save(update_fields=['auth_code'])
        return menu
    meta = MenuMeta.objects.create(title=title, sort=0)
    return Menu.objects.create(
        name=auth_code.split(':')[-1],
        type=MenuType.BUTTON,
        status=CommonStatus.ENABLED,
        sort=0,
        pid=parent,
        creator='system',
        meta=meta,
        auth_code=auth_code,
    )


def get_button(auth_code):
    """按 auth_code（兼容两种写法）取按钮 Menu。"""
    return Menu.objects.filter(
        auth_code__in=variants_of(auth_code), type=MenuType.BUTTON
    ).first()


def assign(role, menus):
    for menu in menus:
        RolePermission.objects.get_or_create(role=role, menu=menu)


class Command(BaseCommand):
    help = '初始化发布中心三角色（运维/研发技术负责人/研发）及权限矩阵'

    def handle(self, *args, **options):
        # 0. 清理重复的按钮权限（同一 auth_code 仅保留一条，避免 get() 返回多条）
        dup_codes = (
            Menu.objects.filter(type=MenuType.BUTTON)
            .values('auth_code')
            .annotate(cnt=Count('id'))
            .filter(cnt__gt=1)
        )
        for d in dup_codes:
            ac = d['auth_code']
            dups = Menu.objects.filter(
                auth_code__in=variants_of(ac), type=MenuType.BUTTON
            ).order_by('id')
            keep = dups.first()
            dups.exclude(id=keep.id).delete()
            self.stdout.write(f'清理重复按钮权限: {ac}（保留 ID={keep.id}）')

        # 1. 角色
        ops = ensure_role(
            'ops', '运维', 'all', '运维：拥有所有模块、全部数据权限'
        )
        lead = ensure_role(
            'dev_lead', '研发技术负责人', 'all', '技术负责人：模块全量维护 + 发布触发，全部数据'
        )
        dev = ensure_role(
            'developer', '研发', 'custom', '研发：按分配应用维护（数据范围=自定义）'
        )

        # 2. 确保标准 + 自定义按钮存在，建立 auth_code -> Menu 映射
        button_menus = {}
        for model in RELEASE_MODELS:
            for action in STANDARD:
                code = f'release:{model}:{action}'
                button_menus[code] = ensure_button(
                    code, STANDARD_TITLE[action], PATH_MAP.get(model)
                )
            for action in CUSTOM.get(model, []):
                code = f'release:{model}:{action}'
                button_menus[code] = ensure_button(
                    code, action.replace('-', ' ').title(), PATH_MAP.get(model)
                )
            for action in APPROVE_CUSTOM.get(model, []):
                code = f'release:{model}:{action}'
                button_menus[code] = ensure_button(
                    code, action.title(), PATH_MAP.get(model)
                )

        # 数据权限管理页菜单：应用权限分配（挂在 system 目录下，仅运维/技术负责人可见）
        system_catalog = Menu.objects.filter(
            type=MenuType.CATALOG, path__in=['/system', '/system/']
        ).first()
        dp_menu_meta, _ = MenuMeta.objects.get_or_create(
            title='应用权限分配',
            defaults={
                'icon': 'mdi:account-key-outline',
                'sort': 0,
                'affix_tab': False,
                'badge': '',
                'badge_type': '',
                'badge_variants': '',
                'iframe_src': '',
                'link': '',
                'hide_children_in_menu': False,
                'hide_in_menu': False,
            },
        )
        dp_menu, _ = Menu.objects.get_or_create(
            name='DataPermission',
            path='/system/data-permission',
            defaults={
                'status': CommonStatus.ENABLED,
                'type': MenuType.MENU,
                'component': '/system/data-permission/index',
                'auth_code': 'system:data_permission_rule:view',
                'pid': system_catalog,
                'meta': dp_menu_meta,
                'sort': 9,
                'creator': 'system',
            },
        )
        self.stdout.write(f'应用权限分配菜单: ID={dp_menu.id}')

        # 数据权限管理（应用权限分配页）按钮：仅运维 / 技术负责人可管理
        dp_buttons = []
        for action in STANDARD:
            code = f'system:data_permission_rule:{action}'
            dp_buttons.append(ensure_button(code, STANDARD_TITLE[action], dp_menu.path))

        def release_buttons(actions_by_model):
            menus = []
            for model, actions in actions_by_model.items():
                for a in actions:
                    m = get_button(f'release:{model}:{a}')
                    if m:
                        menus.append(m)
                    # 兼容 edit / update 写法，两者都绑上，避免前端按钮因码不一致不显示
                    alt = EDIT_ALT.get(a)
                    if alt:
                        m2 = get_button(f'release:{model}:{alt}')
                        if m2 and m2 not in menus:
                            menus.append(m2)
            return menus

        # 全量动作（标准 + 自定义 + 审批）
        full_actions = {
            m: STANDARD + CUSTOM.get(m, []) + APPROVE_CUSTOM.get(m, [])
            for m in RELEASE_MODELS
        }
        # 研发动作矩阵（等同应用维护权限）
        dev_actions = {
            'application': STANDARD + CUSTOM['application'],
            'config_package': STANDARD,
            'application_pipeline_config': STANDARD,
            'release_record': ['query', 'create', 'edit', 'trigger', 'cancel', 'retry'],
            'sync_log': ['query'],
            'project': ['query'],
            'module': ['query'],
            'code_repository': ['query'],
            'pipeline_template': ['query'],
            'approval_rule': ['query'],
        }

        # 3. 导航菜单（release 全部可见；system 运维全部、技术负责人只读）
        release_nav = list(Menu.objects.filter(
            Q(path__startswith='/release') | Q(component__startswith='/release/')
        ))
        system_nav = list(Menu.objects.filter(
            type__in=[MenuType.CATALOG, MenuType.MENU], path__startswith='/system/'
        ))
        # 仪表盘/首页（分析页、工作台、概览）：所有登录用户可见，独立于 release/system 路径
        dashboard_nav = list(Menu.objects.filter(
            type__in=[MenuType.CATALOG, MenuType.MENU]
        ).filter(
            Q(component__startswith='/dashboard/') | Q(path__in=['/analytics', '/workspace'])
        ))
        system_query_buttons = list(Menu.objects.filter(
            type=MenuType.BUTTON, auth_code__startswith='system:',
            auth_code__endswith=':query'
        ))
        system_all_buttons = list(Menu.objects.filter(
            type=MenuType.BUTTON, auth_code__startswith='system:'
        ))

        # 4. 清空并按矩阵重新分配（幂等）
        RolePermission.objects.filter(role__in=[ops, lead, dev]).delete()

        # 运维：字面“所有权限”——绑定全部导航菜单 + 全部按钮（含前端/其他脚本新建的）
        all_nav = list(Menu.objects.filter(type__in=[MenuType.CATALOG, MenuType.MENU]))
        all_buttons = list(Menu.objects.filter(type=MenuType.BUTTON))
        assign(ops, all_nav + all_buttons)

        assign(lead, release_nav + dashboard_nav + release_buttons(full_actions)
               + system_nav + system_query_buttons + dp_buttons)
        assign(dev, release_nav + dashboard_nav + release_buttons(dev_actions))

        self.stdout.write(self.style.SUCCESS(
            f'发布中心角色权限初始化完成：\n'
            f'  - {ops.name}({ops.code}) 数据范围={ops.data_scope}，权限数={RolePermission.objects.filter(role=ops).count()}\n'
            f'  - {lead.name}({lead.code}) 数据范围={lead.data_scope}，权限数={RolePermission.objects.filter(role=lead).count()}\n'
            f'  - {dev.name}({dev.code}) 数据范围={dev.data_scope}，权限数={RolePermission.objects.filter(role=dev).count()}'
        ))
