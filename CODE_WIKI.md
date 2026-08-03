# Code Wiki — BigData-DevOps 发布管理平台

> 本文档是对 bigdata-devops 仓库的结构化 Code Wiki，涵盖项目整体架构、主要模块职责、关键类与函数说明、依赖关系以及项目运行方式。

## 目录

- [1. 项目概述](#1-项目概述)
- [2. 技术架构总览](#2-技术架构总览)
- [3. 项目目录结构](#3-项目目录结构)
- [4. 后端 backend（Django）](#4-后端-backenddjanGo)
  - [4.1 入口与配置](#41-入口与配置)
  - [4.2 system 系统管理模块](#42-system-系统管理模块)
  - [4.3 release 发布系统模块（核心业务）](#43-release-发布系统模块核心业务)
  - [4.4 ai 模块](#44-ai-模块)
  - [4.5 utils 工具层](#45-utils-工具层)
  - [4.6 middleware 中间件](#46-middleware-中间件)
- [5. AI 服务 ai_service（FastAPI）](#5-ai-服务-ai_servicefastapi)
- [6. 前端 web（Vue3 vben-admin）](#6-前端-webvue3-vben-admin)
- [7. 依赖关系](#7-依赖关系)
- [8. 项目运行方式](#8-项目运行方式)
- [9. 核心业务流程](#9-核心业务流程)

---

## 1. 项目概述

本项目是一个面向企业的 **DevOps 发布管理平台**（bigdata-devops），基于 Django5 + Vue3（vben-admin）全栈开发，并新增独立的 FastAPI AI 服务。其核心价值在于：

1. **统一管理 GitLab / Jenkins / Harbor 三套 DevOps 工具链**，通过中央配置 + 服务层封装，屏蔽各工具 API 差异；
2. **基于模板的流水线配置**（PipelineTemplate + Version），支持变量替换、版本快照、回滚；
3. **完整的发布生命周期**（创建 → 审批 → 构建 → 部署 → 回滚 → AI 分析）；
4. **细粒度数据权限**（项目级隔离 + 角色 data_scope + 中央授权表 + 按钮权限码）；
5. **AI 赋能**（构建失败自动分析 + 多 LLM 适配器 + 流式聊天 + 文生图）。

**技术栈**：

| 层 | 技术 |
| --- | --- |
| 后端 | Python 3.12、Django 5.2、DRF 3.16、Celery 5.5、MySQL 8、Redis 7 |
| AI 服务 | FastAPI 0.116、SQLAlchemy 2.0、LangChain 0.3、通义/DeepSeek/OpenAI |
| 前端 | Vue 3.5、Vite 6、TypeScript、Pinia 3、Ant Design Vue 4、vben-admin 5.5 |
| 部署 | Docker Compose、Nginx、Gunicorn、Flower |

**体验地址**：https://demo.ywwuzi.cn （admin/admin123、chenze/admin123）；文档地址：https://docs.ywwuzi.cn

---

## 2. 技术架构总览

### 2.1 整体分层架构

```
┌──────────────────────────────────────────────────────────────┐
│                     前端 web (Vue3 vben-admin)                  │
│   web-antd(主) / web-ele / web-naive / backend-mock(Nitro)     │
└────────────┬───────────────────────────────┬──────────────────┘
             │ /api/admin                     │ /api/ai (SSE)
             ▼                                ▼
┌────────────────────────────┐   ┌──────────────────────────────┐
│   backend (Django + DRF)    │   │   ai_service (FastAPI)        │
│  system / release / ai      │   │   chat(流式) / drawing(文生图) │
│  Celery 异步任务            │   │   复用 Django Token 认证        │
└──────┬─────────────────────┘   └──────────────┬───────────────┘
       │ REST API                                 │ LangChain SDK
       ▼                                         ▼
┌──────────────────────────────────────────────────────────────┐
│   GitLab API │ Jenkins API │ Harbor API │ LLM 厂商(通义/DeepSeek)│
└──────────────────────────────────────────────────────────────┘
       ▲                                         ▲
       │                                         │
┌──────┴───────────┐                    ┌────────┴─────────┐
│  MySQL (django_vue) │共享数据表(authtoken_token / system_users / ai_*)│
│  Redis (缓存/队列)   │                    └──────────────────┘
└──────────────────┘
```

### 2.2 后端分层

| 层 | 模块 | 职责 |
| --- | --- | --- |
| 入口层 | [settings.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/backend/settings.py)、[urls.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/backend/urls.py)、[celery.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/backend/celery.py) | Django/Celery/DRF 配置与路由聚合 |
| 中间件层 | [middleware/](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/middleware) | 演示模式禁写、POST 幂等性 |
| 视图层 | `*/views/` | REST API，ViewSet + 函数视图 |
| 序列化层 | `*/serializers.py` | 模型序列化、校验、脱敏 |
| 模型层 | `*/models.py` | ORM 模型定义 |
| 服务层 | [release/services/](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/release/services) | GitLab/Jenkins/Harbor API 封装 |
| 任务层 | `*/tasks.py` | Celery 异步任务（CI/CD 核心） |
| 工具层 | [utils/](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/utils) | 数据权限、认证、分页、导出、脱敏 |
| 信号层 | [release/signals.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/release/signals.py) | 状态聚合自动维护 |
| LLM 适配层 | [ai/llm/](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/ai/llm) | 多 LLM 提供商统一接口 |

---

## 3. 项目目录结构

```
bigdata-devops/
├── backend/                 # Django 后端（系统管理 + 发布系统 + AI）
│   ├── backend/             # 项目配置（settings/urls/celery/asgi/wsgi）
│   ├── system/              # 系统管理 app（用户/角色/菜单/部门/字典/配置/数据权限）
│   ├── release/             # 发布系统 app（项目/模块/应用/仓库/流水线模板/发布记录）
│   ├── ai/                  # AI app（API Key/模型/对话/绘画/知识库/工具）
│   ├── utils/               # 工具层（认证/权限/分页/导出/脱敏/数据权限）
│   ├── middleware/          # 中间件（演示模式/幂等性）
│   ├── data/                # 静态数据（省市区.xlsx）
│   ├── examples/            # 示例（脱敏）
│   ├── manage.py
│   └── requirements.txt
├── ai_service/              # FastAPI 独立 AI 服务（流式对话/文生图）
│   ├── api/v1/              # 路由与 VO（chat/drawing）
│   ├── services/            # 业务编排
│   ├── llm/                 # LLM 适配器（base/factory/enums/adapter/*）
│   ├── models/              # SQLAlchemy ORM
│   ├── schemas/             # Pydantic 模型
│   ├── crud/                # 通用 CRUD 基类
│   ├── db/                  # 数据库会话
│   ├── deps/                # 认证依赖
│   ├── utils/               # JWT/响应封装
│   ├── main.py / config.py
│   └── requirements.txt
├── web/                     # 前端 monorepo（pnpm workspace + turborepo）
│   ├── apps/
│   │   ├── web-antd/        # 主前端（Ant Design Vue）
│   │   ├── web-ele/         # Element Plus 版
│   │   ├── web-naive/       # Naive UI 版
│   │   └── backend-mock/    # Nitro 模拟后端
│   ├── packages/            # @vben/* 核心包与 UI Kit
│   ├── internal/            # 构建工具（vite-config/vsh/tsconfig）
│   ├── docs/                # VitePress 文档站
│   └── package.json
├── docker/                  # Docker 环境变量（.env.dev/.env.prod/.env.example）
├── docs/                    # Docusaurus 项目文档（prd/essential）
├── sql/                     # 数据库脚本（django_vue.sql/release_menu.sql/system_config.sql）
├── images/                  # 截图资源
├── docker-compose.dev.yml   # 开发环境编排
├── docker-compose.prod.yml  # 生产环境编排
└── README.md
```

---

## 4. 后端 backend（Django）

### 4.1 入口与配置

#### manage.py
[backend/manage.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/manage.py) — Django 标准入口，指定 `DJANGO_SETTINGS_MODULE = 'backend.settings'`，可执行 runserver/migrate/makemigrations 及自定义命令（`import_jenkins_jobs`、`generate_crud`、`setup_release_menu` 等）。

#### settings.py
[backend/backend/settings.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/backend/settings.py) 关键配置：

- **INSTALLED_APPS**：`simpleui`（admin 美化）+ Django 标准六项 + `rest_framework`、`django_filters`、`corsheaders`、`rest_framework.authtoken` + 业务 `system`、`ai`、`release`。
- **自定义用户模型**：`AUTH_USER_MODEL = 'system.User'`。
- **REST_FRAMEWORK**：分页 `utils.pagination.CustomPagination`（PAGE_SIZE=20）；过滤后端 OrderingFilter + DjangoFilterBackend + SearchFilter；认证 `utils.authentication.BearerTokenAuthentication`（Bearer Token）+ Basic/Session/Token；默认权限 `AllowAny`（细粒度由各 ViewSet 的 `HasButtonPermission` 控制）。
- **数据库**：MySQL `django_vue`，通过 `DB_USER/DB_PASSWORD/DB_HOST` 环境变量注入。
- **Redis**：`django_redis.cache.RedisCache`，Session 走 cache。
- **Celery**：Broker 与 Result Backend 均为 `redis://.../0`；`CELERY_BEAT_SCHEDULE` 注册 `system.tasks.sync_temu_order` 定时任务。
- **演示模式**：`DEMO_MODE` 为 True 时动态追加 `DemoModeMiddleware` 并禁用 admin 路由。
- **本地覆盖**：若存在 `backend/local_settings.py` 则导入。
- **AI 默认密钥**：`DEEPSEEK_API_KEY`、`DASHSCOPE_API_KEY` 从环境变量读取。

#### celery.py
[backend/backend/celery.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/backend/celery.py) — `app = Celery('backend')`，`config_from_object('django.conf:settings', namespace='CELERY')`，`autodiscover_tasks()` 自动发现各 app 的 `tasks.py`；Windows 下强制 `worker_pool='solo'`。

#### urls.py
[backend/backend/urls.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/backend/urls.py) — 路由聚合：
- `api/admin/system/` → `system.urls`
- `api/admin/ai/` → `ai.urls`
- `api/admin/release/` → `release.urls`
- `api-auth/` → DRF 登录视图
- 非 DEMO_MODE 时 `admin/` → Django admin（simpleui）

### 4.2 system 系统管理模块

应用配置 [system/apps.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/system/apps.py)（`SystemConfig`）。

#### 4.2.1 数据模型 models.py
[system/models.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/system/models.py) — 所有模型继承 `utils.models.CoreModel`（含 `remark/creator/modifier/create_time/update_time/is_deleted` 审计字段）。

| 模型 | 表名 | 关键字段/职责 |
| --- | --- | --- |
| `MenuMeta` | `system_menu_meta` | 菜单元数据：title/icon/sort/affix_tab/badge/iframe_src/hide_in_menu 等 |
| `Menu` | `system_menu` | 自关联 pid，`type`（catalog/menu/button/embedded/link），`auth_code`（权限编码），OneToOne `meta` |
| `Dept` | `system_dept` | 自关联部门，name/status/leader/phone/email |
| `Role` | `system_role` | name/code/status，`data_scope`（all/custom/dept/self），M2M `permissions` 经 `RolePermission` 关联 Menu |
| `RolePermission` | `system_role_permission` | role FK + menu FK 中间表 |
| `DictType` / `DictData` | `system_dict_type` / `system_dict_data` | 字典类型与字典项 |
| `Post` | `system_post` | 岗位 code/name/sort/status |
| `User` | `system_users` | 继承 `AbstractUser + CoreModel`，扩展 mobile/nickname/gender/city，M2M dept/role/post |
| `LoginLog` | `system_login_log` | 登录日志 username/result(0失败1成功)/user_ip/location |
| `Config` | `system_config` | **DevOps 配置中心**：存储 gitlab_url/token、jenkins_url/user/token、harbor_url/user/password 等敏感配置 |
| `CityArea` | `system_city_area` | 省市区数据 |
| `DataPermissionRule` | `system_data_permission_rule` | **数据权限引擎核心**：scope_type(资源类型)/scope_id/user/level，唯一约束 (scope_type, scope_id, user) |

#### 4.2.2 视图层 views/
[system/views/](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/system/views) 主要视图集：

- **[user.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/system/views/user.py)**
  - `UserLogin(ObtainAuthToken)` — `POST /system/login/`，校验密码+状态，`Token.objects.get_or_create`，异步 `update_user_login_info` 写登录日志（含 IP 地理位置），返回 accessToken。
  - `UserInfo(APIView)` — `GET /system/info/`，返回用户信息 + roles + permissions（超管取全部 button auth_code，普通用户取角色关联的）。
  - `UserViewSet(CustomModelViewSet)` — 用户 CRUD，支持 Excel 导出（`export_fields`），`UserFilter` 支持部门递归过滤。
  - `Logout(APIView)` — 登出。

- **[role.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/system/views/role.py)** — `RoleViewSet`，`assign_permissions` action 清空角色原权限按 `menu_ids` 重建。

- **[menu.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/system/views/menu.py)** — `MenuViewSet`，`tree` action 返回菜单树，`user_menu` 返回当前用户可见菜单（按 role 过滤，排除 button），含名称/路径查重。

- **[dept.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/system/views/dept.py)** — `DeptViewSet`，`tree` action 一次性构建部门树。

- **[config.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/system/views/config.py)** — `ConfigViewSet`，DevOps 服务配置管理。

- **[data_permission.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/system/views/data_permission.py)** — `DataPermissionRuleViewSet`，关键 action：`scope_users`（资源下被授权用户）、`user_scopes`（用户被授权资源）、`assign`（**覆盖式批量分配**）。物理删除。

- **dict_type.py / dict_data.py / post.py / login_log.py / city_area.py** — 标准 CRUD，`dict_data` 的 `simple` action 返回启用的简化字典列表。

#### 4.2.3 tasks.py
[system/tasks.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/system/tasks.py) — `update_user_login_info` 异步写登录日志，`get_location_from_ip` 调 `http://ip-api.com/json` 获取地理位置。

#### 4.2.4 management/commands/
含 `setup_release_menu`、`setup_release_permissions`、`setup_release_roles`、`setup_system_config_menu`、`generate_crud`（基于模板生成前后端 CRUD）、`import_city_area_data`（从 xlsx 导入）、`import_jenkins_jobs`（批量导入 Jenkins Jobs）、`migrate_data_permission_to_project` 等。

### 4.3 release 发布系统模块（核心业务）

应用配置 [release/apps.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/release/apps.py) — `ready()` 中导入 `signals` 注册信号。

#### 4.3.1 数据模型 models.py
[release/models.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/release/models.py)

**资源层级模型**：

| 模型 | 表名 | 说明 |
| --- | --- | --- |
| `Project` | `release_project` | 项目，对应 GitLab Group，含 `gitlab_group_id` 及同步状态字段 |
| `Module` | `release_module` | 模块，对应 GitLab Subgroup（Project 子组），唯一约束 (project, code) |
| `CodeRepository` | `release_code_repository` | 代码仓库（直接继承 Model），repository_type(gitlab/github/gitee)，git_url/git_http_url，default_branch |
| `Application` | `release_application` | **核心业务实体**：project/module/code_repository FK，app_type(java/nodejs/python/go/vue/react)，build_command，dockerfile_path；三套同步状态（gitlab/jenkins/harbor），关键方法 `refresh_jenkins_sync_status()` 聚合应用级 Jenkins 同步状态 |
| `ConfigPackage` | `release_config_package` | 配置包（zip），file_path/checksum/sync_status |
| `SyncLog` | `release_sync_log` | 同步日志，sync_type(harbor/jenkins/ansible)，action(create/update/delete)，status(0失败/1成功) |

**流水线模板系统**：

| 模型 | 表名 | 说明 |
| --- | --- | --- |
| `PipelineTemplate` | `release_pipeline_template` | 模板，name/code/language/framework/is_official，属性 `latest_version` |
| `PipelineTemplateVersion` | `release_pipeline_template_version` | 模板版本，content(Jenkinsfile)/variables(JSON)/stages(JSON)/change_log/is_latest，方法 `auto_increment_version()` 语义化版本递增 |
| `ApplicationPipelineConfig` | `release_application_pipeline_config` | **应用×环境维度配置**，唯一约束 (application, environment)，含 jenkins_sync_status/config_dirty/jenkins_job_name，方法 `get_config_version()` |
| `ApplicationPipelineVersion` | `release_application_pipeline_version` | 配置版本快照（content + variables_snapshot + stages_snapshot），支持回滚 |
| `EnvironmentStrategy` | `release_environment_strategy` | 环境策略，requires_approval/auto_deploy/is_default |

**发布管理**：

| 模型 | 表名 | 说明 |
| --- | --- | --- |
| `ReleaseRecord` | `release_record` | 发布主记录：branch/environment/version，审批信息，Jenkins 构建（job_name/build_number/build_url/build_status），docker_image，状态机（pending/approval_pending/approved/rejected/building/build_success/build_failed/deploying/deployed/rollback/cancelled），`conversation_id` 关联 AI 对话用于构建失败分析。方法 `can_trigger()`/`can_cancel()`/`can_approve()` |
| `ReleaseBuildLog` | `release_build_log` | 构建日志，log_content/stage_name/stage_status |
| `ApprovalRule` | `release_approval_rule` | 审批规则，rule_type(single/any/all/sequential)/approvers/min_approvers |

#### 4.3.2 视图层 views/
[release/views/](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/release/views)

- **[application.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/release/views/application.py)** — `ApplicationViewSet(DataPermissionMixin, CustomModelViewSet)`，scope_type='project'。`perform_create` 自动给创建人授权 + 异步创建 Jenkins/Harbor 资源。action：sync_resources/sync_gitlab/sync_harbor/resource_status/sync_to_jenkins/jenkins_sync_status/preview_jenkinsfile/generate_config。

- **[project.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/release/views/project.py)** — `ProjectViewSet`，`perform_create` 创建人授权 + 创建 GitLab Group；`perform_destroy` 软删除（校验关联应用/模块）。action：modules/applications/tree/sync_gitlab/sync_logs、GitLab 导入系列。

- **[module.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/release/views/module.py)** — `ModuleViewSet`，创建前校验项目数据权限 + 创建 GitLab Subgroup。

- **[code_repository.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/release/views/code_repository.py)** — `CodeRepositoryViewSet`，`_sync_to_gitlab` 按 module.subgroup → project.group 优先级创建 GitLab Project；`import_gitlab_projects` 异步批量导入。

- **[pipeline_template.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/release/views/pipeline_template.py)** — 模板与版本管理。action：create_version/preview/copy/export_config/import_config；版本 `set_latest`，destroy 保护（最新版本/被关联版本不可删）。

- **[application_pipeline.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/release/views/application_pipeline.py)** — `ApplicationPipelineConfigViewSet`，**核心配置管理**。`perform_create` 同应用同环境覆盖式更新（version+1），`perform_update` 自动 +1 并置 config_dirty。action：generate（变量替换生成 Jenkinsfile + 创建快照）/rollback/sync_to_jenkins/generate_and_sync。另含**命名规则 API**：`validate_naming`、`generate_standard_names`（生成 GitLab/Harbor/Jenkins/Ansible 标准化资源名）。

- **[release.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/release/views/release.py)** — `ReleaseRecordViewSet` + 函数视图。
  - action：trigger（异步 `trigger_jenkins_build`）/cancel（停止 Jenkins 构建）/logs/approve/reject/retry/**ai_analysis**（仅 build_failed 可分析，拼接 system_prompt + 截断日志创建 AI 对话，返回 conversation_id）。
  - 函数视图 `trigger_release(request, app_id)` — **核心发布入口**，按 `EnvironmentStrategy.requires_approval` 判定审批，创建 ReleaseRecord，无需审批则同步测试 Jenkins 连接后异步触发构建。
  - `get_app_branches`/`get_app_environments`/`get_approval_rules` 辅助接口。

- **[statistics.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/release/views/statistics.py)** — 总体统计、按日趋势、应用发布排行。

#### 4.3.3 serializers.py
[release/serializers.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/release/serializers.py) — `ProjectSerializer` 附加 module_count/app_count/gitlab_group_url；`ApplicationSerializer` 附加 `pipeline_sync_summary`（各环境同步状态明细）；`ApplicationCreateSerializer` 从 code_repository 自动回填 git_url。

#### 4.3.4 tasks.py（Celery 异步任务，CI/CD 核心）
[release/tasks.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/release/tasks.py)

**资源创建三件套**：
- `create_gitlab_resources(app_id)` — 在模块 Subgroup 下创建 GitLab Project，失败重试 3 次。
- `create_jenkins_resources(app_id)` — 遍历应用所有 PipelineConfig，创建 folder 层级 `project/module/app` + job `env_code`。
- `create_harbor_resources(app_id)` — 创建 Harbor Project（命名 `{project.code}-{module.code}`）。
- `sync_all_resources(app_id)` — chain 按序执行 GitLab → Jenkins → Harbor。

**Jenkins 配置同步**：
- `sync_application_jenkins(app_id)` — 批量同步应用所有启用配置，先置同步中 + refresh 聚合状态，逐个同步后再聚合。
- `sync_jenkins_config(config_id)` — 优先用最新 ApplicationPipelineVersion.content，否则实时渲染模板（`${key}` 替换），调 `jenkins.update_job_config` 更新 XML。**区分旧 job（按原路径）和新 job（folder=project/module/app + name=env_code）**。

**发布构建流程**：
- `trigger_jenkins_build(release_id)` — 加载 ReleaseRecord + PipelineConfig，构建 10 个参数（PROJECT/MODULE/APP/BRANCH/VERSION/ENVIRONMENT/GIT_REPO/CODE_SUBPATH/BUILD_COMMAND/PACKAGE_NAME），解析 jenkins_job_name 为 folder+job_name，校验 Job 存在后 `jenkins.build_job` 触发 + 轮询新构建号，更新状态为 building，异步触发 `poll_build_status`。
- `poll_build_status(release_id)` — 每 10s 轮询 `jenkins.get_build_info`，building 时异步 `fetch_build_log` + 继续轮询，完成时按 result 更新状态（SUCCESS→build_success，其他→build_failed）。
- `fetch_build_log(release_id)` — 拉控制台日志写入 ReleaseBuildLog。

**代码仓库同步**：
- `sync_code_repository_gitlab(repo_id)` — 按"组→子组→仓库"逻辑创建 GitLab Project。
- `import_gitlab_projects_batch(items, username)` — 批量导入，按 GitLab namespace full_path 自动匹配 project/module，支持软删除恢复。

#### 4.3.5 pipeline_utils.py
[release/pipeline_utils.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/release/pipeline_utils.py)
- `get_template_content(config)` — 优先 template_version.content，回退 template.latest_version。
- `build_pipeline_variables(app, config, template_variables_def)` — 构建变量字典，优先级：**应用字段注入 → 模板默认值 → 用户覆盖（config.variables）**。注入 APP_NAME/APP_CODE/GIT_URL/GIT_REPO/BUILD_BRANCH/BUILD_COMMAND/CODE_SUBPATH/DOCKERFILE_PATH/PROJECT_NAME/MODULE_NAME。

#### 4.3.6 signals.py
[release/signals.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/release/signals.py) — `pipeline_config_post_save` 接收器，ApplicationPipelineConfig post_save 时自动调 `application.refresh_jenkins_sync_status()` 重新聚合应用级 Jenkins 同步状态，保证环境级配置变更后应用级状态实时一致。

#### 4.3.7 services/（DevOps 服务层）
[release/services/](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/release/services)

- **[base.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/release/services/base.py)**
  - `DevOpsException` — 统一异常（message/service/details）。
  - `ConfigService` — **配置中心**，从 `system.Config` 表读配置，5 分钟 Redis 缓存（`devops_config:` 前缀），提供 `get_gitlab_config`/`get_jenkins_config`/`get_harbor_config`。
  - `BaseService` — 日志封装基类。

- **[jenkins_service.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/release/services/jenkins_service.py)** — `JenkinsService(BaseService)`，封装 Jenkins REST API。HTTPBasicAuth + CSRF Crumb；`_build_job_path("a/b/c")` → `/job/a/job/b/job/c`；folder 幂等创建；Pipeline Job 创建/更新（SCM 模式 + 内联脚本模式）；构建触发/轮询/日志/停止。

- **[gitlab_service.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/release/services/gitlab_service.py)** — `GitLabService(BaseService)`，封装 GitLab v4 API（Private-Token），Group/Subgroup/Project CRUD + 搜索分页。

- **[harbor_service.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/release/services/harbor_service.py)** — `HarborService(BaseService)`，封装 Harbor v2.0 API（Basic Auth，禁用 SSL 校验支持自签名），Project 创建/查询。

- **[config_package_service.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/release/services/config_package_service.py)** — 生成应用配置包（zip），写入 config.json + 模板文件，计算 checksum。

#### 4.3.8 urls.py
[release/urls.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/release/urls.py) — DefaultRouter 注册 13 个 ViewSet + 独立 path（trigger-release/app-branches/app-environments/approval-rules-list/statistics/statistics-trend/statistics-app-rank）。

### 4.4 ai 模块

[ai/](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/ai)

#### 4.4.1 数据模型 models.py
[ai/models.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/ai/models.py) — 定义 11 个 ORM 模型：

| 模型 | 表名 | 关键字段 |
| --- | --- | --- |
| `AIApiKey` | `ai_api_key` | name/platform/api_key/url/status |
| `AIModel` | `ai_model` | name/model/platform/temperature/max_tokens/max_contexts，key FK |
| `Tool` | `ai_tool` | name/description/status |
| `Knowledge` | `ai_knowledge` | name/embedding_model/top_k/similarity_threshold |
| `KnowledgeDocument` | `ai_knowledge_document` | knowledge FK/name/url/content/tokens |
| `KnowledgeSegment` | `ai_knowledge_segment` | content/vector_id/retrieval_count |
| `ChatRole` | `ai_chat_role` | name/avatar/model_id FK/system_message，M2M knowledge/tools |
| `ChatConversation` | `ai_chat_conversation` | title/user/role/model_id/model/temperature/max_tokens/max_contexts |
| `ChatMessage` | `ai_chat_message` | conversation_id(BigIntegerField 非FK)/type(user/assistant)/content |
| `Drawing` | `ai_drawing` | platform/model/prompt/width/height/status/pic_url/task_id |

#### 4.4.2 choices.py
[ai/choices.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/ai/choices.py) — `PlatformChoices` 含 17 个平台（OpenAI/AzureOpenAI/Ollama/TongYi/DeepSeek/DouBao/HunYuan/SiliconFlow/ZhiPu/MiniMax/Moonshot/BaiChuan 等）；`MessageType`（user/assistant）。

#### 4.4.3 LLM 适配器层
[ai/llm/](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/ai/llm)

- **[base.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/ai/llm/base.py)** — `MultiModalAICapability(ABC)` 抽象基类，定义对话/图片生成/视频生成/知识库/语音合成能力接口，默认全部 `raise NotImplementedError`。
- **[enums.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/ai/llm/enums.py)** — `LLMProvider` 枚举（DEEPSEEK/TONGYI/OPENAI/GOOGLE_GENAI）。
- **[factory.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/ai/llm/factory.py)** — `get_adapter(provider, api_key, model, **kwargs)` 工厂方法。
- **adapter/**：
  - [deepseek.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/ai/llm/adapter/deepseek.py) — 基于 `ChatDeepSeek`，实现 chat/stream_chat。
  - [openai.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/ai/llm/adapter/openai.py) — 基于 `ChatOpenAI`，支持 base_url（兼容 AzureOpenAI/Ollama/SiliconFlow/ZhiPu）。
  - [tongyi.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/ai/llm/adapter/tongyi.py) — 基于 `ChatTongyi` + `dashscope.ImageSynthesis`，**唯一实现文生图**（async_call + fetch 轮询）。
  - [genai.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/ai/llm/adapter/genai.py) — Google GenAI 占位实现。

#### 4.4.4 视图层
[ai/views/](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/ai/views)

- **[chat_message.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/ai/views/chat_message.py)** — `ChatMessageViewSet`，核心 `stream` action（POST `/stream/`）：
  - `PLATFORM_TO_PROVIDER` 映射：OpenAI/AzureOpenAI/Ollama/SiliconFlow/ZhiPu → OPENAI；DeepSeek → DEEPSEEK；TongYi → TONGYI。
  - `_get_conversation_config` 从 conversation.model_id.key 解析 (provider, api_key, base_url, model)，无配置时回退到环境变量。
  - 写 user 消息 → 加载历史上下文 → `get_adapter(...).stream_chat(context)` → **同步视图内手动驱动 async generator**（asyncio.new_event_loop + run_until_complete）→ SSE `data: ...\n\n` 推送 → 流结束写 assistant 消息。
  - 返回 `StreamingHttpResponse(content_type='text/event-stream')`。

- **[chat_conversation.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/ai/views/chat_conversation.py)** — `ChatConversationViewSet`，create 时按 platform 选模型别名（deepseek→deepseek-chat，tongyi→qwen-plus）。

- **[drawing.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/ai/views/drawing.py)** — `DrawingViewSet`，create 调 TongYiAdapter.create_drawing_task（async_call），retrieve 轮询状态更新 pic_url。

- **ai_api_key.py / ai_model.py / knowledge.py / tool.py** — 标准 CRUD，AIApiKeySerializer 继承 `DesensitizationMixin`（api_key 脱敏）。

#### 4.4.5 urls.py
[ai/urls.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/ai/urls.py) — 注册 7 个 ViewSet：api_key/ai_model/tool/knowledge/chat_conversation/chat_message/drawing。

### 4.5 utils 工具层

[backend/utils/](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/utils)

| 文件 | 关键类/函数 | 职责 |
| --- | --- | --- |
| [models.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/utils/models.py) | `CoreModel`、`AutoCommentModel`、`CommonStatus` | 所有业务模型基类（审计字段），自动 db_comment |
| [authentication.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/utils/authentication.py) | `BearerTokenAuthentication` | DRF Token 认证支持 `Bearer` 前缀 |
| [custom_model_viewSet.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/utils/custom_model_viewSet.py) | `CustomModelViewSet` | 所有业务 ViewSet 基类：action_serializers、**自动推断权限码** `{app_label}:{model}:{action}`、追加 HasButtonPermission、支持批量创建、标准化响应 |
| [data_permission.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/utils/data_permission.py) | `DataPermissionMixin`、`resolve_data_scope`、`get_allowed_scope_ids`、`user_has_scope_access`、`user_has_button_perm` | **通用数据权限引擎**：SCOPE_MODELS 注册表、4 种 data_scope（all/custom/dept/self）、中央授权表查询、`DataPermissionMixin` 声明 scope_type/scope_field 即接入 |
| [decorators.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/utils/decorators.py) | `idempotent(timeout=10)` | DRF 接口幂等性装饰器（MD5 + Redis） |
| [export_mixin.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/utils/export_mixin.py) | `ExportMixin` | `export_data` action，支持 excel/csv，pandas 生成 |
| [filters_logs.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/utils/filters_logs.py) | `IgnoreSQLFilter` | 日志过滤器，忽略噪声 SQL |
| [idempotency_helper.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/utils/idempotency_helper.py) | `generate_idempotency_key`、`check_idempotency` | 幂等性辅助（MD5 + Redis） |
| [ip_utils.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/utils/ip_utils.py) | `get_client_ip` | 按 8 个 HTTP 头优先级解析真实 IP |
| [pagination.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/utils/pagination.py) | `CustomPagination` | page_size=20，超页码返回空列表，响应格式 `{code,message,data:{total,items}}` |
| [permissions.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/utils/permissions.py) | `HasButtonPermission`、`HasMutateButtonPermission` | 通用按钮权限，自动推断权限码，超管直通，未登记权限码不拦截 |
| [serializers.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/utils/serializers.py) | `AuditUserFieldsMixin`、`DesensitizationMixin`、`CustomModelSerializer` | 审计字段自动赋值、**敏感字段脱敏**（保留前4后4）、动态字段裁剪（_fields/_exclude） |
| [string_utils.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/utils/string_utils.py) | `camel_to_snake` | 驼峰转蛇形（权限码推断用） |
| [utils.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/utils/utils.py) | `validate_mobile`、`validate_amount`、`to_cent`、`ts_to_aware` | 通用校验与转换 |

### 4.6 middleware 中间件

- **[DemoModeMiddleware.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/middleware/DemoModeMiddleware.py)** — `DemoModeMiddleware`：演示环境全局禁止 POST/PUT/PATCH/DELETE（白名单 login/logout），返回 403。
- **[IdempotencyMiddleware.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/middleware/IdempotencyMiddleware.py)** — `IdempotencyMiddleware`：全局 POST 幂等性，10s 内重复提交返回 409。

---

## 5. AI 服务 ai_service（FastAPI）

[ai_service/](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/ai_service) — 基于 FastAPI 的独立 AI 多模态服务，通过统一 LLM 适配器对接多家厂商，提供流式对话（SSE）与文生图（异步任务）。**复用 Django 的 `authtoken_token` 与 `system_users` 表共享登录态**。

### 5.1 入口与配置

- **[main.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/ai_service/main.py)** — `load_dotenv()` 加载环境变量；`FastAPI()` 实例；CORS 白名单 `http://localhost` 与 `http://localhost:8010`；注册路由前缀 `/api/ai/v1`；`GET /ping` 健康检查。
- **[config.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/ai_service/config.py)** — 仅数据库配置，从环境变量读取（DB_USER/DB_PASSWORD/DB_HOST/DB_PORT/DB_NAME，默认 django_vue），拼接 `mysql+pymysql://...`。
- **Dockerfile** — 多阶段：base（python:3.12.2 + 阿里云源安装依赖）→ prod（`gunicorn main:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8010 --workers 4`）。

### 5.2 API 与路由层

- **[api/v1/__init__.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/ai_service/api/v1/__init__.py)** — `api_v1_router = APIRouter(prefix="/api/ai/v1")`，挂载 chat_router 与 drawing_router。
- **[api/v1/chat/__init__.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/ai_service/api/v1/chat/__init__.py)** — 4 个端点：
  - `POST /chat/stream` — **流式对话核心**，按 platform 选模型与 API Key（tongyi→qwen-plus+DASHSCOPE_API_KEY，默认 deepseek→deepseek-chat+DEEPSEEK_API_KEY），工厂创建适配器，写 user 消息，组装上下文，`async for chunk in llm.stream_chat(context)` 以 SSE 推送，流结束写 AI 消息。
  - `POST /chat/conversations` / `GET /chat/conversations` — 创建/获取会话列表。
  - `GET /chat/messages` — 获取会话消息列表。
- **[api/v1/drawing/__init__.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/ai_service/api/v1/drawing/__init__.py)** — 3 个端点：分页查询、创建文生图任务（TongYiAdapter.create_drawing_task）、查询任务状态（轮询）。
- **[routers/base.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/ai_service/routers/base.py)** — `GenericRouter` 泛型路由（create/get_multi/get/update/remove），当前未实例化使用，为后续管理类资源预留。

### 5.3 服务层 services/

- **[chat_service.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/ai_service/services/chat_service.py)** — `ChatDBService` 静态方法类：get_conversation/get_or_create_conversation/update_conversation_title/add_message/insert_ai_message/get_history。
- **[drawing_service.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/ai_service/services/drawing_service.py)** — create_drawing_task（解析 size 宽高写表）/fetch_drawing_task_status（轮询 TongYiAdapter 更新 status 与 pic_url）/get_drawing_page。

### 5.4 LLM 适配器层（核心）

- **[llm/base.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/ai_service/llm/base.py)** — `MultiModalAICapability(ABC)`，能力声明式设计，子类按需覆写，`stream_chat` 为异步生成器（yield）。
- **[llm/factory.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/ai_service/llm/factory.py)** — `get_adapter(provider, api_key, model, **kwargs)` 简单工厂。
- **[llm/enums.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/ai_service/llm/enums.py)** — `LLMProvider`（DEEPSEEK/TONGYI/OPENAI/GOOGLE_GENAI）。
- **adapter/**：
  - [deepseek.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/ai_service/llm/adapter/deepseek.py) — `ChatDeepSeek`，chat/stream_chat。
  - [openai.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/ai_service/llm/adapter/openai.py) — `ChatOpenAI`，对话实现，文生图占位。
  - [tongyi.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/ai_service/llm/adapter/tongyi.py) — `ChatTongyi` + `dashscope.ImageSynthesis`，**唯一实现文生图**（async_call 异步提交 + fetch 轮询）。
  - [genai.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/ai_service/llm/adapter/genai.py) — Google GenAI 占位。

**LLM 交互方式总结**：

| 厂商 | 对话 | 文生图 | 底层 SDK | 调用模式 |
| --- | --- | --- | --- | --- |
| DeepSeek | ✅ ainvoke/astream | ❌ | langchain_deepseek.ChatDeepSeek | 兼容 OpenAI API，流式 |
| 通义千问 | ✅ ainvoke/astream | ✅ 异步任务 | langchain_community.ChatTongyi + dashscope.ImageSynthesis | 对话流式；图片异步轮询 |
| OpenAI | ✅ ainvoke/astream | ❌（DALL·E 占位） | langchain_openai.ChatOpenAI | 流式 |
| Google GenAI | ❌ 占位 | ❌ | (无) | 未实现 |

### 5.5 数据模型与基础设施

- **[models/base.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/ai_service/models/base.py)** — `CoreModel` 基类（id/remark/creator/modifier/create_time/update_time/is_deleted）。
- **[models/user.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/ai_service/models/user.py)** — `AuthToken`（表 authtoken_token）+ `DjangoUser`（表 system_users），复用 Django 用户体系。
- **[models/ai.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/ai_service/models/ai.py)** — 11 个 ORM 模型（与 backend/ai 同构）。
- **[db/session.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/ai_service/db/session.py)** — `create_engine(pool_pre_ping=True)` + `SessionLocal` + `get_db()` 依赖。
- **[deps/auth.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/ai_service/deps/auth.py)** — `get_current_user` 依赖，解析 Bearer Token → 查 Authtoken → 查 DjangoUser → 返回 user dict。
- **[utils/resp.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/ai_service/utils/resp.py)** — `Response`/`resp_success`/`resp_error` 统一响应（成功码 0）。
- **[crud/base.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/ai_service/crud/base.py)** — `CRUDBase` 泛型 CRUD 基类。

---

## 6. 前端 web（Vue3 vben-admin）

[web/](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/web) — 基于 **pnpm workspace + Turborepo** 的 monorepo，名为 `vben-admin-monorepo` v5.5.7。引擎要求 node >= 20.10.0、pnpm >= 9.12.0。

### 6.1 整体结构

[package.json](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/web/package.json) 关键脚本：`dev:antd`/`dev:ele`/`dev:naive` 启动各子应用，`build:antd` 单包构建，`check` 串行循环依赖/依赖/类型/拼写检查，`lint`/`format`。

[pnpm-workspace.yaml](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/web/pnpm-workspace.yaml) 声明 `internal/*`、`packages/*`、`packages/@core/*`、`packages/effects/*`、`apps/*`、`docs` 等目录，内嵌 `catalog:` 统一版本管理。

[Dockerfile](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/web/Dockerfile) 多阶段：base（node:22.17.0 + pnpm@10.10.0）→ build（`npm run build:antd`）→ prod（nginx:1.25-alpine 托管 dist，EXPOSE 5268）。**生产以 web-antd 为主前端**。

**子应用一览**：

| 子应用 | 定位 |
| --- | --- |
| `apps/web-antd` | **主前端**，Ant Design Vue 4，含 AI 对话/绘画、系统管理、发布管理完整业务 |
| `apps/web-ele` | Element Plus 版，业务较精简（system 模块） |
| `apps/web-naive` | Naive UI 版，业务最精简（仅 _core） |
| `apps/backend-mock` | Nitro 模拟后端，提供 mock 接口 |

### 6.2 web-antd 主前端

#### 6.2.1 构建配置
[vite.config.mts](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/web/apps/web-antd/vite.config.mts) — **双后端代理**：`/api/admin` → `VITE_BACKEND_URL`（默认 http://localhost:8000），`/api/ai` → `VITE_AI_URL`（默认 http://localhost:8010）；host 0.0.0.0、port 5678；自定义 [vite-plugin-oss.mjs](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/web/apps/web-antd/plugins/vite-plugin-oss.mjs)（构建后用 ali-oss 上传 dist，可选删除本地）。

#### 6.2.2 启动流程
[main.ts](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/web/apps/web-antd/src/main.ts) → [bootstrap.ts](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/web/apps/web-antd/src/bootstrap.ts) → [app.vue](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/web/apps/web-antd/src/app.vue)：

```
main.ts
 ├─ initPreferences(namespace, overridesPreferences)   # 偏好初始化（accessMode='backend'）
 └─ dynamic import('./bootstrap')
     └─ bootstrap(namespace)
         ├─ initComponentAdapter() / initSetupVbenForm()   # AntD 组件适配
         ├─ createApp(App)
         ├─ registerLoadingDirective                     # v-loading/v-spinning
         ├─ setupI18n(app)                              # i18n + antd locale + dayjs
         ├─ initStores(app, { namespace })              # Pinia + 持久化
         ├─ registerAccessDirective(app)                # v-access（内置）
         ├─ registerPermissionDirective(app)            # v-permission（自定义）
         ├─ initTippy(app)
         ├─ app.use(router)                             # createRouterGuard 已挂载
         ├─ app.use(MotionPlugin)
         └─ app.mount('#app')
 ↓
app.vue
 ├─ useAntdDesignTokens() + 主题算法（dark/compact）
 ├─ useDictStore().fetchDictData()                    # 启动拉字典
 └─ <ConfigProvider><App><RouterView/></App></ConfigProvider>
```

#### 6.2.3 请求封装 request.ts
[api/request.ts](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/web/apps/web-antd/src/api/request.ts) — 基于 `@vben/request` 的 `RequestClient`：
- 请求拦截器：注入 `Authorization: Bearer xxx` + `Accept-Language`。
- 响应拦截器1：`defaultResponseInterceptor`（code===0 提取 data）。
- 响应拦截器2：`authenticateResponseInterceptor`（401 自动 refresh token）。
- 响应拦截器3：`errorMessageResponseInterceptor`（antd message.error 兜底）。
- 导出 `requestClient`（返回 data）与 `baseRequestClient`（原始，用于 refresh/logout）。

业务 API：
- [api/core/](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/web/apps/web-antd/src/api/core) — auth（login/refresh/logout）、menu（`GET /system/menu/user_menu`）、user（`GET /system/info/`）。
- [api/ai/](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/web/apps/web-antd/src/api/ai) — chat/drawing，**因 SSE 流式走独立 `fetchWithAuth`**（[utils/fetch-with-auth.ts](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/web/apps/web-antd/src/utils/fetch-with-auth.ts)），按 `\n\n` 分块解析 `data:` SSE 流。
- [api/system/](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/web/apps/web-antd/src/api/system) — dept/menu/role/dict_data/dict_type/tenants。
- [api/release/](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/web/apps/web-antd/src/api/release) — project/module/record。

**请求链路**：
```
组件 → xxxApi (requestClient)
  ↓ 请求拦截器: Authorization + Accept-Language
Vite proxy (/api/admin → 8000, /api/ai → 8010)
  ↓
后端
  ↓ 响应 { code, data, error, message }
拦截器1: code===0 提取 data
拦截器2: 401 → doRefreshToken → 重试；失败 → doReAuthenticate
拦截器3: 兜底 message.error
  ↓
组件拿到 data
```

#### 6.2.4 状态管理 Store
[store/](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/web/apps/web-antd/src/store)：

| Store | 职责 |
| --- | --- |
| `useAuthStore`（[auth.ts](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/web/apps/web-antd/src/store/auth.ts)） | authLogin（登录→setToken→fetchUserInfo→跳转）、fetchUserInfo（设 userInfo + permissions）、logout |
| `useDictStore`（[dict.ts](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/web/apps/web-antd/src/store/dict.ts)） | 字典数据，fetchDictData/getOptionsByType |
| `usePermissionStore`（[permission.ts](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/web/apps/web-antd/src/store/permission.ts)） | 按钮权限码 permissions/hasPermission（web-antd 独有） |

`useAccessStore`/`useUserStore` 来自 `@vben/stores`。

#### 6.2.5 路由与权限守卫
[router/](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/web/apps/web-antd/src/router)：
- [access.ts](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/web/apps/web-antd/src/router/access.ts) — `generateAccess`，`import.meta.glob('../views/**/*.vue')` 收集页面组件，字符串组件名映射。
- [guard.ts](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/web/apps/web-antd/src/router/guard.ts) — `setupAccessGuard`（核心权限守卫）：核心路由放行 → 无 token 跳登录 → 已检查放行 → 否则 fetchUserInfo → generateAccess 生成动态路由 → setIsAccessChecked → 重定向。

**权限控制（三维度）**：
- **菜单/路由权限**：accessMode='backend'，后端 `getAllMenusApi()` 返回菜单树，`generateAccessible` 映射字符串组件名到页面组件。
- **按钮权限（双轨制）**：Vben 内置 `v-access`（基于 accessCodes）+ web-antd 自定义 `v-permission`（[utils/permission.ts](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/web/apps/web-antd/src/utils/permission.ts)，基于 permissionStore），两者数据源均为 `userInfo.permissions`。

#### 6.2.6 通用 CRUD Model
[models/base.ts](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/web/apps/web-antd/src/models/base.ts) — `BaseModel<T>` 通用 CRUD 基类，构造接收 baseUrl，提供 list/retrieve/create/update/patch/delete/export/action 方法，业务模型继承并指定 baseUrl 即获完整 CRUD（如 [models/ai/tool.ts](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/web/apps/web-antd/src/models/ai/tool.ts)）。

### 6.3 backend-mock 模拟后端

[apps/backend-mock/](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/web/apps/backend-mock) — 基于 Nitro（`nitropack` + `@faker-js/faker` + `jsonwebtoken`）的本地 mock 后端。

- [nitro.config.ts](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/web/apps/backend-mock/nitro.config.ts) — `/api/**` 开启 CORS。
- [middleware/1.api.ts](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/web/apps/backend-mock/middleware/1.api.ts) — 全局中间件，`/api/system/` 下写操作返回 403（演示保护）。
- [utils/jwt-utils.ts](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/web/apps/backend-mock/utils/jwt-utils.ts) — JWT 签发/校验（accessToken 7d / refreshToken 30d）。
- [utils/mock-data.ts](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/web/apps/backend-mock/utils/mock-data.ts) — MOCK_USERS（vben/admin/jack）、MOCK_CODES、MOCK_MENUS。
- [utils/response.ts](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/web/apps/backend-mock/utils/response.ts) — `useResponseSuccess`/`usePageResponseSuccess`/`forbiddenResponse`。
- api/ — auth（login/refresh/logout）、user/info、menu/all、system/dept|menu|role/list、table/list、upload 等。

### 6.4 web-ele 与 web-naive 差异

三者结构同构，差异主要在 UI 库与组件适配：

| 维度 | web-antd | web-ele | web-naive |
| --- | --- | --- | --- |
| UI 库 | ant-design-vue 4 | element-plus 2.9 | naive-ui 2.41 |
| 业务模块 | ai/release/system 完整 | system 精简 | 仅 _core |
| store | auth + dict + permission | auth + permission | 仅 auth |
| 权限指令 | v-access + v-permission | v-access + v-permission | 仅 v-access |
| 代理 | /api/admin + /api/ai 双代理 | /api 单代理 | /api 单代理 |

---

## 7. 依赖关系

### 7.1 模块间依赖

```
web (前端)
  ├─ /api/admin → backend (Django) ── system / release / ai
  └─ /api/ai   → ai_service (FastAPI) ── 复用 Django Token 认证

backend
  ├─ system.Config ──→ ConfigService ──→ GitLabService / JenkinsService / HarborService
  ├─ release.tasks ──→ 三个 Service（调用外部 GitLab/Jenkins/Harbor API）
  ├─ ai.views.chat_message ──→ ai.llm.factory ──→ langchain + dashscope SDK ──→ 外部 LLM
  └─ Celery ──→ Redis (broker/backend)

ai_service
  ├─ deps.auth ──→ models.user (authtoken_token / system_users 表，与 backend 共享 MySQL)
  └─ llm.adapter ──→ langchain + dashscope ──→ 外部 LLM
```

**关键共享点**：ai_service 与 backend 共用同一 MySQL `django_vue` 库，通过 `authtoken_token` 表实现 Token 认证共享，前端同一 Bearer Token 可同时访问两个后端。

### 7.2 后端关键依赖（[requirements.txt](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/requirements.txt)）

| 依赖 | 版本 | 用途 |
| --- | --- | --- |
| Django | 5.2.1 | Web 框架 |
| djangorestframework | 3.16.0 | REST API |
| django-filter / django-cors-headers | 25.1 / 4.7.0 | 过滤 / CORS |
| mysqlclient | 2.2.7 | MySQL 驱动 |
| celery / redis / django_redis / flower / eventlet | 5.5.3 / 6.2.0 / 6.0.0 / 2.0.1 / 0.40.0 | 异步任务与监控 |
| requests | 2.32.3 | GitLab/Jenkins/Harbor HTTP 调用 |
| pandas / openpyxl | 2.2.3 / 3.1.5 | 数据导出 Excel/CSV |
| langchain / langchain-openai / langchain-deepseek / langchain-community / dashscope | 0.3.x / 0.3.28 / 0.1.3 / 0.3.26 / 1.23.8 | LLM 集成 |
| gunicorn / django-simpleui | 23.0.0 / 2025.5.17 | 部署 / Admin 美化 |

### 7.3 AI 服务关键依赖（[requirements.txt](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/ai_service/requirements.txt)）

| 依赖 | 版本 | 用途 |
| --- | --- | --- |
| fastapi | 0.116.1 | Web 框架 |
| uvicorn[standard] / gunicorn | 0.35.0 / 23.0.0 | ASGI 服务器 |
| SQLAlchemy / PyMySQL | 2.0.41 / 1.1.1 | ORM / MySQL 驱动 |
| langchain / langchain-openai / langchain-deepseek / langchain-community / dashscope | 0.3.x | LLM 编排 |

### 7.4 前端关键依赖

Vue 3.5、Vite 6、Pinia 3、Ant Design Vue 4、vben-admin 5.5、TypeScript、TailwindCSS、dayjs、@vueuse/core、markdown-it + highlight.js（AI 对话渲染）、ali-oss（OSS 上传）、nitropack（mock）。

### 7.5 外部服务依赖

- **MySQL 8**：数据库 `django_vue`
- **Redis 7**：Celery broker/backend + Django 缓存/Session
- **GitLab**：代码仓库托管（v4 API，Private-Token）
- **Jenkins**：CI/CD 构建引擎（REST API + CSRF Crumb）
- **Harbor**：镜像仓库（v2.0 API，Basic Auth）
- **LLM 厂商**：通义千问（DashScope）、DeepSeek、OpenAI

---

## 8. 项目运行方式

### 8.1 环境要求

- Python 3.12、Node v22.17.0、pnpm 10.10.0
- MySQL 8、Redis 7

### 8.2 后端启动（Django）

```bash
cd backend
# 1. 修改 backend/backend/settings.py 中 DATABASES 数据库连接
# 2. 安装依赖
pip install -r requirements.txt
# 3. 导入数据库
mysql -h 127.0.0.1 -u root -p -e "CREATE DATABASE IF NOT EXISTS django_vue DEFAULT CHARSET utf8mb4 COLLATE utf8mb4_unicode_ci;"
mysql -h 127.0.0.1 -u root -p django_vue < ./sql/django_vue.sql
# 4. 启动
python manage.py runserver
```

**Celery（可选）**：
```bash
celery -A backend worker -l info        # Worker
celery -A backend beat -l info          # 定时任务
celery -A backend flower --port=5555 --basic_auth=admin:admin123   # 监控
```

### 8.3 AI 服务启动（FastAPI）

```bash
cd ai_service
pip install -r requirements.txt
# 配置 .env（DEEPSEEK_API_KEY / DASHSCOPE_API_KEY）
uvicorn main:app --host 0.0.0.0 --port 8010 --reload
# 生产：gunicorn main:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8010 --workers 4
```

### 8.4 前端启动

```bash
cd web
pnpm install
npm run dev:antd      # 主前端，端口 5678
# 或 npm run dev:ele / dev:naive
```

### 8.5 Docker 一键部署

**开发环境**：
```bash
cp docker/.env.example docker/.env.local   # 修改配置
docker compose -f docker-compose.dev.yml up -d --build
```
开发编排服务：db（MySQL，43306）、redis（46379）、backend（48000）、web（45678）、celery_worker、celery_beat、flower（45555）。

**生产环境**：
```bash
cp docker/.env.example docker/.env.local
docker compose -f docker-compose.prod.yml up -d --build
```
生产编排服务：db（33306）、redis（36379）、backend（gunicorn，38000）、frontend（nginx，35678）、celery_worker、celery_beat、flower（35555）。

### 8.6 关键环境变量

| 变量 | 作用 | 默认 |
| --- | --- | --- |
| `DB_USER/DB_PASSWORD/DB_HOST` | MySQL 连接 | root/admin123456/127.0.0.1 |
| `DEMO_MODE` | 演示模式（禁写） | False |
| `DEEPSEEK_API_KEY` / `DASHSCOPE_API_KEY` | LLM 密钥 | - |
| `VITE_BACKEND_URL` / `VITE_AI_URL` | 前端代理目标 | localhost:8000 / 8010 |
| `VITE_OSS_ENABLED` | 前端 OSS 上传 | false |
| `VITE_ROUTER_HISTORY` | 路由模式 | history |

### 8.7 初始化数据

- [sql/django_vue.sql](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/sql/django_vue.sql) — 完整数据库 dump（表结构 + 初始数据）
- [sql/system_config.sql](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/sql/system_config.sql) — DevOps 服务配置（gitlab/jenkins/harbor url 与凭证）
- [sql/release_menu.sql](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/sql/release_menu.sql) — 发布管理菜单初始化
- management 命令：`setup_release_menu`、`setup_system_config_menu`、`import_jenkins_jobs` 等

---

## 9. 核心业务流程

### 9.1 CI/CD 发布主线

```
项目创建 (ProjectViewSet.perform_create)
  ├─ 写 DataPermissionRule(scope_type='project', level='owner')
  └─ GitLabService.create_group → 更新 gitlab_group_id + SyncLog

模块创建 (ModuleViewSet.perform_create)
  ├─ 校验项目数据权限
  └─ GitLabService.create_group(parent=project.gitlab_group_id) → Subgroup

代码仓库创建 (CodeRepositoryViewSet._sync_to_gitlab)
  └─ GitLabService.create_project(namespace=subgroup or group)

应用创建 (ApplicationViewSet.perform_create)
  ├─ 从 code_repository 回填 git_url
  ├─ 写 DataPermissionRule(scope_type='project', level='owner')
  ├─ create_jenkins_resources.delay(app_id)
  │   └─ JenkinsService.create_pipeline_job_with_folder (folder=project/module/app, job=env_code)
  └─ create_harbor_resources.delay(app_id)
      └─ HarborService.create_project(name=project-module)

配置 Pipeline (ApplicationPipelineConfigViewSet)
  ├─ generate → build_pipeline_variables → ${key} 替换 → ApplicationPipelineVersion 快照
  └─ sync_to_jenkins → sync_jenkins_config.delay(config_id)
      └─ JenkinsService.update_job_config (内联脚本 XML)

触发发布 (trigger_release)
  ├─ EnvironmentStrategy.requires_approval 判定
  ├─ 创建 ReleaseRecord (approval_pending or pending)
  └─ 无需审批 → trigger_jenkins_build.delay(release_id)
      ├─ 解析 jenkins_job_name → folder + job_name
      ├─ JenkinsService.build_job (带 10 个参数)
      ├─ 更新 ReleaseRecord(jenkins_build_number, status=building)
      ├─ poll_build_status.delay (10s 轮询)
      │   ├─ building → fetch_build_log + 继续轮询
      │   └─ 完成 → 更新 status (build_success/build_failed) + fetch_build_log
      └─ 失败可 retry / ai_analysis (创建 ChatConversation 分析日志)
```

### 9.2 应用接入流程

1. 创建 Project → 自动创建 GitLab Group + 给创建人授权 project 数据权限。
2. 创建 Module → 校验项目数据权限 + 创建 GitLab Subgroup。
3. 创建 CodeRepository → 同步到 GitLab Project（同步执行）。
4. 创建 Application → 关联 CodeRepository（自动回填 git_url）+ 异步创建 Jenkins Jobs + Harbor Project + 给创建人授权。
5. 配置 ApplicationPipelineConfig（选模板 + 填变量）→ generate Jenkinsfile（创建版本快照）→ sync_to_jenkins（异步同步 Job XML）。
6. 触发发布 trigger_release → 创建 ReleaseRecord（按环境策略决定是否审批）→ trigger_jenkins_build（带参数构建）→ poll_build_status 轮询 → fetch_build_log 拉日志 → 更新状态。
7. 构建失败可 retry，可 ai_analysis 创建 AI 对话分析日志。

### 9.3 模板版本管理机制

- PipelineTemplate 有多个 PipelineTemplateVersion，其中一个 `is_latest=True`。
- 创建/更新版本时若设为 latest，自动取消同模板其他版本的 latest 标记。
- 应用配置 `template` + `template_version`（可空，空则用 template.latest_version）。
- generate 时创建 ApplicationPipelineVersion 快照（content + variables_snapshot + stages_snapshot），支持 rollback。
- 最新版本和被应用关联的版本不可删除。
- 编辑 Stage 自动创建新版本（版本号自动递增），不修改原版本。

### 9.4 Jenkins Job 命名规则

- **新建**：`folder = project.code/module.code/app.code`，`job_name = environment_code`，完整路径 `project/module/app/env`。
- **导入（旧 job）**：保留原始 `jenkins_job_name` 全路径，同步时按原路径更新，不重命名。

### 9.5 应用级同步状态聚合（refresh_jenkins_sync_status）

由 [signals.py](file:///Users/tengyun/.trae-cn/worktrees/bigdata-devops/feat-generate-code-wiki-YbpElz/backend/release/signals.py) 在 ApplicationPipelineConfig post_save 时自动维护：

- 无启用配置 → 5 未配置
- 任一同步中 → 1 同步中
- 任一失败 → 3 部分环境同步失败
- 有 dirty 或待同步 → 4 待重新同步
- 全部已同步 → 2 全部环境已同步

### 9.6 流式对话数据流（ai_service）

```
Client POST /api/ai/v1/chat/stream (body: content, conversation_id, platform)
  ↓ Authorization: Bearer <token>
get_current_user → 解析 token → user dict
  ↓
chat_stream → 选 platform → get_adapter(factory) → DeepSeek/TongYi Adapter
  ↓ ChatDBService.get_conversation → db.merge → add_message(用户消息)
  ↓ get_history → 组装 [("system",...), (hist.type, hist.content), ...]
  ↓ llm.stream_chat(context) → async for chunk → SSE "data: {chunk}\n\n"
  ↓ 流结束 → ChatDBService.insert_ai_message(完整 AI 回复)
  ↓
Client (text/event-stream)
```

### 9.7 文生图数据流（异步任务模式）

```
阶段一：提交
POST /api/ai/v1/drawing/ (CreateDrawingTaskRequest)
  → TongYiAdapter.create_drawing_task
  → dashscope.ImageSynthesis.async_call → rsp{task_id, task_status=PENDING}
  → services.create_drawing_task → 写 Drawing 表
  ← {id, task_id, status}

阶段二：轮询
GET /api/ai/v1/drawing/{id}/
  → fetch_drawing_task_status
  → 若 PENDING/RUNNING → TongYiAdapter.fetch_drawing_task_status(task_id)
  → dashscope.ImageSynthesis.fetch → rsp{output.task_status, results[0].url}
  → SUCCEEDED 更新 status + pic_url；FAILED 更新 error_message
  ← {id, status, pic_url, error_message}
```

---

> **文档说明**：本 Code Wiki 基于仓库当前代码静态分析生成，覆盖项目整体架构、三大模块（backend / ai_service / web）的职责与关键类函数、依赖关系及运行方式。所有关键文件均以 `file:///` 绝对路径链接标注，便于在 IDE 中直接跳转查看源码。
