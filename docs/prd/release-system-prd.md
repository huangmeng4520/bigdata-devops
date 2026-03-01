# 发布系统 PRD（产品需求文档）

**版本**: v1.0  
**作者**: DevOps团队  
**日期**: 2026-03-01  
**状态**: 待评审

---

## 目录

- [1. 文档概述](#1-文档概述)
- [2. 项目背景与目标](#2-项目背景与目标)
- [3. 用户角色与场景](#3-用户角色与场景)
- [4. 业务架构设计](#4-业务架构设计)
- [5. 功能需求](#5-功能需求)
- [6. 技术实现规范](#6-技术实现规范)
- [7. 数据模型设计](#7-数据模型设计)
- [8. 接口设计](#8-接口设计)
- [9. 配置包规范](#9-配置包规范)
- [10. 非功能性需求](#10-非功能性需求)
- [11. 开发计划](#11-开发计划)
- [12. 风险与应对](#12-风险与应对)

---

## 1. 文档概述

### 1.1 编写目的

本文档定义了发布系统的产品需求，用于指导后端、前端开发人员进行系统开发，以及测试人员进行测试用例设计。

### 1.2 适用范围

- 后端开发团队
- 前端开发团队
- 测试团队
- 运维团队
- 产品经理

### 1.3 术语定义

| 术语 | 说明 |
|------|------|
| 项目（Project） | 业务系统的顶层分类，如"大数据平台"、"政务服务平台" |
| 模块（Module） | 项目下的业务模块划分，如"数据采集模块"、"数据治理模块" |
| 应用（Application） | 模块下的具体应用服务，如"user-service"、"data-api" |
| 互联网区 | 可访问互联网的网络区域，部署GitLab、Jenkins、Harbor等 |
| 政务网 | 与互联网隔离的内网区域，通过网闸单向获取配置 |
| 配置包 | 包含政务网侧资源配置的JSON/YAML文件压缩包 |
| 网闸 | 奇安信网闸设备，仅允许HTTPS单向访问 |

---

## 2. 项目背景与目标

### 2.1 项目背景

当前企业采用多级业务架构（项目→模块→应用），在CI/CD流程中存在以下问题：

1. **资源创建分散**：GitLab仓库、Jenkins任务、Harbor项目需分别手动创建，效率低下
2. **命名不规范**：缺乏统一命名规范，导致资源命名混乱，难以管理
3. **跨网配置困难**：互联网区与政务网隔离，配置同步依赖人工操作，易出错
4. **权限管理粗放**：缺乏细粒度的权限控制，无法满足多团队协作需求

### 2.2 项目目标

#### 2.2.1 核心目标

1. **一站式创建**：通过自研Web系统一次性完成互联网侧的GitLab仓库、Jenkins任务、Harbor项目创建
2. **配置自动化同步**：生成配置包通过网闸同步到政务网，自动创建对应资源
3. **规范化管理**：建立统一的命名规范和模板化创建流程
4. **权限精细化**：支持项目-模块-应用三级的权限控制

#### 2.2.2 量化指标

| 指标 | 目标值 |
|------|--------|
| 应用创建时间 | 从30分钟降低到5分钟 |
| 配置同步成功率 | ≥99% |
| 命名规范符合率 | 100% |
| 系统可用性 | ≥99.9% |

---

## 3. 用户角色与场景

### 3.1 用户角色

| 角色 | 职责 | 权限范围 |
|------|------|----------|
| **系统管理员** | 系统配置、全局参数管理 | 所有功能和数据 |
| **项目经理** | 项目级管理、审批 | 所属项目及下级模块、应用 |
| **开发负责人** | 模块级管理、应用创建申请 | 所属模块及下级应用 |
| **开发人员** | 查看应用信息、触发构建 | 所属应用的查看和构建权限 |
| **运维人员** | 配置同步、系统监控 | 配置包管理、日志查看 |

### 3.2 核心场景

#### 场景1：新应用创建

**角色**：开发负责人  
**前置条件**：已存在所属项目、模块

**流程**：
1. 登录系统，进入【发布管理】→【应用管理】
2. 点击【新建应用】，填写应用信息
3. 系统自动校验命名规范
4. 提交申请，项目经理审批
5. 审批通过后，系统自动：
   - 调用GitLab API创建仓库
   - 调用Jenkins API创建CI任务
   - 调用Harbor API创建项目
   - 生成配置包并上传
6. 运维人员触发或定时任务自动同步到政务网
7. 政务网侧自动创建对应资源
8. 通知相关人员创建完成

#### 场景2：配置同步

**角色**：运维人员  
**前置条件**：配置包已生成

**流程**：
1. 定时任务每5分钟检查配置包更新
2. 通过网闸下载最新配置包
3. 解析配置包，调用政务网API创建资源
4. 记录同步日志
5. 同步失败时告警

#### 场景3：应用发布

**角色**：开发人员  
**前置条件**：应用已创建，代码已推送

**流程**：
1. 进入【发布管理】→【应用列表】
2. 选择应用，点击【构建】
3. 触发Jenkins CI任务
4. 查看构建日志
5. 构建成功后镜像推送到Harbor
6. Harbor同步到政务网
7. 触发政务网Jenkins部署任务

---

## 4. 业务架构设计

### 4.1 总体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         互联网区                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│  │   GitLab    │    │  Jenkins    │    │   Harbor    │        │
│  │  代码仓库   │    │  CI/CD任务  │    │  镜像仓库   │        │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘        │
│         │                  │                  │                │
│         └──────────────────┼──────────────────┘                │
│                           │                                    │
│                    ┌──────┴──────┐                            │
│                    │  自研Web    │                            │
│                    │  发布系统   │                            │
│                    └──────┬──────┘                            │
│                           │                                    │
│                    ┌──────┴──────┐    ┌─────────────┐        │
│                    │  配置包     │───→│  文件服务器  │        │
│                    │  生成器     │    │   (Nginx)   │        │
│                    └─────────────┘    └──────┬──────┘        │
└──────────────────────────────────────────────┼─────────────────┘
                                               │
                                        ┌──────┴──────┐
                                        │   网闸      │
                                        │  (HTTPS)    │
                                        └──────┬──────┘
                                               │
┌──────────────────────────────────────────────┼─────────────────┐
│                         政务网                │                 │
│                           ┌──────────────────┴──────┐         │
│                           │  定时任务/调度器         │         │
│                           └──────────┬──────────────┘         │
│                                      │                         │
│         ┌────────────────────────────┼────────────────────┐   │
│         │                            │                    │   │
│  ┌──────┴──────┐    ┌───────────┐    │    ┌───────────┐  │   │
│  │   Harbor    │    │  Jenkins  │    │    │  Ansible  │  │   │
│  │  镜像仓库   │    │  部署任务  │    │    │  配置管理  │  │   │
│  └─────────────┘    └───────────┘    │    └───────────┘  │   │
│                                      │                    │   │
│                           ┌──────────┴──────────┐        │   │
│                           │  apply_config.py    │        │   │
│                           │  配置应用脚本       │        │   │
│                           └─────────────────────┘        │   │
└──────────────────────────────────────────────────────────┴───┘
```

### 4.2 三级业务结构

```
项目（Project）
├── 模块1（Module）
│   ├── 应用1（Application）
│   ├── 应用2（Application）
│   └── 应用3（Application）
├── 模块2（Module）
│   ├── 应用4（Application）
│   └── 应用5（Application）
└── 模块3（Module）
    └── 应用6（Application）
```

### 4.3 命名规范

#### 4.3.1 GitLab命名

| 层级 | 命名规则 | 示例 |
|------|----------|------|
| Group | `{project_code}` | `bigdata-platform` |
| Subgroup | `{project_code}/{module_code}` | `bigdata-platform/data-collect` |
| Repository | `{project_code}/{module_code}/{app_code}` | `bigdata-platform/data-collect/user-service` |

#### 4.3.2 Jenkins命名

| 类型 | 命名规则 | 示例 |
|------|----------|------|
| Folder | `{project_code}` | `bigdata-platform` |
| Job(CI) | `{project_code}/{module_code}/{app_code}-ci` | `bigdata-platform/data-collect/user-service-ci` |
| Job(CD) | `{project_code}/{module_code}/{app_code}-cd` | `bigdata-platform/data-collect/user-service-cd` |

#### 4.3.3 Harbor命名

| 类型 | 命名规则 | 示例 |
|------|----------|------|
| Project | `{project_code}-{module_code}` | `bigdata-platform-data-collect` |
| Image | `{project}/{app}:{version}` | `bigdata-platform-data-collect/user-service:v1.0.0` |
| Robot Account | `robot_{app_code}` | `robot_user-service` |

---

## 5. 功能需求

### 5.1 项目管理

#### 5.1.1 功能列表

| 功能 | 描述 | 优先级 |
|------|------|--------|
| 项目创建 | 创建新项目，设置项目编码、名称、描述 | P0 |
| 项目编辑 | 修改项目信息 | P0 |
| 项目删除 | 软删除项目（需检查关联模块） | P0 |
| 项目列表 | 分页查询项目列表，支持搜索、过滤 | P0 |
| 项目详情 | 查看项目详情，包含统计信息 | P1 |
| 项目成员管理 | 添加/移除项目成员，设置角色 | P1 |

#### 5.1.2 字段定义

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | Long | 是 | 主键ID |
| name | String(64) | 是 | 项目名称 |
| code | String(32) | 是 | 项目编码（唯一，用于命名） |
| description | String(256) | 否 | 项目描述 |
| gitlab_group_id | Integer | 否 | GitLab Group ID |
| status | Integer | 是 | 状态：0-禁用，1-启用 |
| creator | String(64) | 是 | 创建人 |
| create_time | DateTime | 是 | 创建时间 |
| update_time | DateTime | 是 | 更新时间 |
| is_deleted | Boolean | 是 | 是否删除 |

### 5.2 模块管理

#### 5.2.1 功能列表

| 功能 | 描述 | 优先级 |
|------|------|--------|
| 模块创建 | 在项目下创建模块 | P0 |
| 模块编辑 | 修改模块信息 | P0 |
| 模块删除 | 软删除模块（需检查关联应用） | P0 |
| 模块列表 | 查询项目下的模块列表 | P0 |
| 模块详情 | 查看模块详情 | P1 |

#### 5.2.2 字段定义

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | Long | 是 | 主键ID |
| project_id | Long | 是 | 所属项目ID |
| name | String(64) | 是 | 模块名称 |
| code | String(32) | 是 | 模块编码（项目内唯一） |
| description | String(256) | 否 | 模块描述 |
| gitlab_subgroup_id | Integer | 否 | GitLab Subgroup ID |
| status | Integer | 是 | 状态：0-禁用，1-启用 |
| creator | String(64) | 是 | 创建人 |
| create_time | DateTime | 是 | 创建时间 |
| update_time | DateTime | 是 | 更新时间 |
| is_deleted | Boolean | 是 | 是否删除 |

### 5.3 应用管理

#### 5.3.1 功能列表

| 功能 | 描述 | 优先级 |
|------|------|--------|
| 应用创建 | 创建应用并初始化资源（GitLab、Jenkins、Harbor） | P0 |
| 应用编辑 | 修改应用信息 | P0 |
| 应用删除 | 软删除应用（需清理关联资源） | P0 |
| 应用列表 | 分页查询应用列表，支持多条件筛选 | P0 |
| 应用详情 | 查看应用详情，包含CI/CD配置信息 | P0 |
| 应用构建 | 触发Jenkins CI任务 | P0 |
| 构建历史 | 查看应用构建历史记录 | P1 |
| 资源状态 | 查看GitLab、Jenkins、Harbor资源状态 | P1 |

#### 5.3.2 字段定义

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | Long | 是 | 主键ID |
| module_id | Long | 是 | 所属模块ID |
| project_id | Long | 是 | 所属项目ID（冗余字段） |
| name | String(64) | 是 | 应用名称 |
| code | String(32) | 是 | 应用编码（模块内唯一） |
| description | String(256) | 否 | 应用描述 |
| app_type | String(16) | 是 | 应用类型：java、nodejs、python、go、vue、react |
| git_url | String(256) | 是 | Git仓库地址 |
| gitlab_project_id | Integer | 否 | GitLab Project ID |
| jenkins_ci_job | String(128) | 否 | Jenkins CI任务名称 |
| harbor_project | String(64) | 否 | Harbor项目名称 |
| build_branch | String(64) | 否 | 构建分支（默认main） |
| dockerfile_path | String(128) | 否 | Dockerfile路径（默认./Dockerfile） |
| status | Integer | 是 | 状态：0-禁用，1-启用 |
| creator | String(64) | 是 | 创建人 |
| create_time | DateTime | 是 | 创建时间 |
| update_time | DateTime | 是 | 更新时间 |
| is_deleted | Boolean | 是 | 是否删除 |

### 5.4 配置包管理

#### 5.4.1 功能列表

| 功能 | 描述 | 优先级 |
|------|------|--------|
| 配置包生成 | 根据应用配置生成配置包 | P0 |
| 配置包列表 | 查询配置包历史记录 | P0 |
| 配置包下载 | 下载配置包文件 | P0 |
| 配置包详情 | 查看配置包内容和同步状态 | P1 |
| 同步状态 | 查看政务网侧同步状态 | P1 |

#### 5.4.2 字段定义

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | Long | 是 | 主键ID |
| app_id | Long | 是 | 关联应用ID |
| version | String(32) | 是 | 配置包版本 |
| file_path | String(256) | 是 | 配置包文件路径 |
| file_size | Long | 是 | 文件大小（字节） |
| checksum | String(64) | 是 | 文件校验和（SHA256） |
| sync_status | Integer | 是 | 同步状态：0-待同步，1-同步中，2-已同步，3-失败 |
| sync_time | DateTime | 否 | 同步时间 |
| sync_message | String(512) | 否 | 同步消息 |
| creator | String(64) | 是 | 创建人 |
| create_time | DateTime | 是 | 创建时间 |

### 5.5 同步日志

#### 5.5.1 功能列表

| 功能 | 描述 | 优先级 |
|------|------|--------|
| 日志列表 | 查询同步日志列表 | P0 |
| 日志详情 | 查看同步日志详情 | P1 |
| 日志导出 | 导出同步日志 | P2 |

#### 5.5.2 字段定义

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | Long | 是 | 主键ID |
| config_package_id | Long | 否 | 关联配置包ID |
| sync_type | String(16) | 是 | 同步类型：harbor、jenkins、ansible |
| resource_name | String(128) | 是 | 资源名称 |
| action | String(16) | 是 | 操作：create、update、delete |
| status | Integer | 是 | 状态：0-失败，1-成功 |
| message | String(1024) | 否 | 日志消息 |
| create_time | DateTime | 是 | 创建时间 |

### 5.6 系统配置

#### 5.6.1 功能列表

| 功能 | 描述 | 优先级 |
|------|------|--------|
| GitLab配置 | 配置GitLab连接信息 | P0 |
| Jenkins配置 | 配置Jenkins连接信息 | P0 |
| Harbor配置 | 配置Harbor连接信息 | P0 |
| 模板管理 | 管理CI/CD模板（Jenkinsfile、Dockerfile等） | P1 |

---

## 6. 技术实现规范

> **重要说明**：本系统必须基于现有项目技术栈进行迭代开发，严格遵循现有架构规范。

### 6.1 后端技术栈

| 技术 | 版本 | 说明 |
|------|------|------|
| Django | 5.2.1 | Web框架 |
| Django REST Framework | 3.16.0 | API框架 |
| MySQL | 8.0+ | 数据库 |
| Redis | 7.0+ | 缓存/会话 |
| Celery | 5.x | 异步任务 |

### 6.2 前端技术栈

| 技术 | 版本 | 说明 |
|------|------|------|
| Vue | 3.x | 前端框架 |
| Vite | 5.x | 构建工具 |
| TypeScript | 5.x | 类型支持 |
| vben-admin | latest | 后台模板 |
| Ant Design Vue | 4.x | UI组件库 |

### 6.3 后端开发规范

#### 6.3.1 新建Django App

```bash
cd backend
python manage.py startapp release
```

#### 6.3.2 注册应用

在 `backend/backend/settings.py` 中添加：

```python
INSTALLED_APPS = [
    # ... existing apps ...
    "release",  # 发布管理模块
]
```

#### 6.3.3 模型定义规范

所有模型**必须**继承 `utils.models.CoreModel`：

```python
# backend/release/models.py
from django.db import models
from utils.models import CoreModel, CommonStatus


class Project(CoreModel):
    """发布项目"""
    name = models.CharField(max_length=64, verbose_name="项目名称")
    code = models.CharField(max_length=32, unique=True, verbose_name="项目编码")
    description = models.CharField(max_length=256, null=True, blank=True, verbose_name="项目描述")
    gitlab_group_id = models.IntegerField(null=True, blank=True, verbose_name="GitLab Group ID")
    status = models.IntegerField(
        choices=CommonStatus.choices,
        default=CommonStatus.ENABLED,
        verbose_name="状态"
    )
    sort = models.IntegerField(default=0, verbose_name="排序")

    class Meta:
        db_table = "release_project"
        verbose_name = "发布项目"
        verbose_name_plural = verbose_name
        ordering = ["-sort", "-create_time"]

    def __str__(self):
        return self.name


class Module(CoreModel):
    """发布模块"""
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, 
        related_name="modules", verbose_name="所属项目"
    )
    name = models.CharField(max_length=64, verbose_name="模块名称")
    code = models.CharField(max_length=32, verbose_name="模块编码")
    description = models.CharField(max_length=256, null=True, blank=True, verbose_name="模块描述")
    gitlab_subgroup_id = models.IntegerField(null=True, blank=True, verbose_name="GitLab Subgroup ID")
    status = models.IntegerField(
        choices=CommonStatus.choices,
        default=CommonStatus.ENABLED,
        verbose_name="状态"
    )
    sort = models.IntegerField(default=0, verbose_name="排序")

    class Meta:
        db_table = "release_module"
        verbose_name = "发布模块"
        verbose_name_plural = verbose_name
        ordering = ["-sort", "-create_time"]
        unique_together = [["project", "code"]]

    def __str__(self):
        return f"{self.project.name}/{self.name}"


class Application(CoreModel):
    """发布应用"""
    APP_TYPE_CHOICES = [
        ("java", "Java"),
        ("nodejs", "Node.js"),
        ("python", "Python"),
        ("go", "Go"),
        ("vue", "Vue"),
        ("react", "React"),
    ]

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE,
        related_name="applications", verbose_name="所属项目"
    )
    module = models.ForeignKey(
        Module, on_delete=models.CASCADE,
        related_name="applications", verbose_name="所属模块"
    )
    name = models.CharField(max_length=64, verbose_name="应用名称")
    code = models.CharField(max_length=32, verbose_name="应用编码")
    description = models.CharField(max_length=256, null=True, blank=True, verbose_name="应用描述")
    app_type = models.CharField(max_length=16, choices=APP_TYPE_CHOICES, verbose_name="应用类型")
    git_url = models.CharField(max_length=256, null=True, blank=True, verbose_name="Git仓库地址")
    gitlab_project_id = models.IntegerField(null=True, blank=True, verbose_name="GitLab Project ID")
    jenkins_ci_job = models.CharField(max_length=128, null=True, blank=True, verbose_name="Jenkins CI任务")
    harbor_project = models.CharField(max_length=64, null=True, blank=True, verbose_name="Harbor项目")
    build_branch = models.CharField(max_length=64, default="main", verbose_name="构建分支")
    dockerfile_path = models.CharField(max_length=128, default="./Dockerfile", verbose_name="Dockerfile路径")
    status = models.IntegerField(
        choices=CommonStatus.choices,
        default=CommonStatus.ENABLED,
        verbose_name="状态"
    )
    sort = models.IntegerField(default=0, verbose_name="排序")

    class Meta:
        db_table = "release_application"
        verbose_name = "发布应用"
        verbose_name_plural = verbose_name
        ordering = ["-sort", "-create_time"]
        unique_together = [["module", "code"]]

    def __str__(self):
        return f"{self.project.name}/{self.module.name}/{self.name}"


class ConfigPackage(CoreModel):
    """配置包"""
    SYNC_STATUS_CHOICES = [
        (0, "待同步"),
        (1, "同步中"),
        (2, "已同步"),
        (3, "同步失败"),
    ]

    app = models.ForeignKey(
        Application, on_delete=models.CASCADE,
        related_name="config_packages", verbose_name="关联应用"
    )
    version = models.CharField(max_length=32, verbose_name="配置包版本")
    file_path = models.CharField(max_length=256, verbose_name="文件路径")
    file_size = models.BigIntegerField(verbose_name="文件大小(字节)")
    checksum = models.CharField(max_length=64, verbose_name="文件校验和")
    sync_status = models.IntegerField(
        choices=SYNC_STATUS_CHOICES,
        default=0,
        verbose_name="同步状态"
    )
    sync_time = models.DateTimeField(null=True, blank=True, verbose_name="同步时间")
    sync_message = models.CharField(max_length=512, null=True, blank=True, verbose_name="同步消息")

    class Meta:
        db_table = "release_config_package"
        verbose_name = "配置包"
        verbose_name_plural = verbose_name
        ordering = ["-create_time"]

    def __str__(self):
        return f"{self.app.name}_v{self.version}"


class SyncLog(CoreModel):
    """同步日志"""
    ACTION_CHOICES = [
        ("create", "创建"),
        ("update", "更新"),
        ("delete", "删除"),
    ]

    config_package = models.ForeignKey(
        ConfigPackage, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="sync_logs", verbose_name="配置包"
    )
    project = models.ForeignKey(
        Project, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="sync_logs", verbose_name="项目"
    )
    module = models.ForeignKey(
        Module, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="sync_logs", verbose_name="模块"
    )
    app = models.ForeignKey(
        Application, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="sync_logs", verbose_name="应用"
    )
    sync_type = models.CharField(max_length=16, verbose_name="同步类型")
    resource_name = models.CharField(max_length=128, verbose_name="资源名称")
    action = models.CharField(max_length=16, choices=ACTION_CHOICES, verbose_name="操作")
    status = models.IntegerField(verbose_name="状态: 0-失败, 1-成功")
    message = models.CharField(max_length=1024, null=True, blank=True, verbose_name="日志消息")

    class Meta:
        db_table = "release_sync_log"
        verbose_name = "同步日志"
        verbose_name_plural = verbose_name
        ordering = ["-create_time"]


class Template(CoreModel):
    """发布模板"""
    TEMPLATE_TYPE_CHOICES = [
        ("jenkinsfile", "Jenkinsfile"),
        ("dockerfile", "Dockerfile"),
        ("docker-compose", "Docker Compose"),
    ]

    name = models.CharField(max_length=64, verbose_name="模板名称")
    code = models.CharField(max_length=32, unique=True, verbose_name="模板编码")
    template_type = models.CharField(max_length=16, choices=TEMPLATE_TYPE_CHOICES, verbose_name="模板类型")
    app_type = models.CharField(max_length=16, null=True, blank=True, verbose_name="适用应用类型")
    content = models.TextField(verbose_name="模板内容")
    description = models.CharField(max_length=256, null=True, blank=True, verbose_name="模板描述")
    status = models.IntegerField(
        choices=CommonStatus.choices,
        default=CommonStatus.ENABLED,
        verbose_name="状态"
    )

    class Meta:
        db_table = "release_template"
        verbose_name = "发布模板"
        verbose_name_plural = verbose_name
        ordering = ["-create_time"]

    def __str__(self):
        return self.name
```

#### 6.3.4 序列化器规范

```python
# backend/release/serializers.py
from rest_framework import serializers
from .models import Project, Module, Application, ConfigPackage, SyncLog, Template


class ProjectSerializer(serializers.ModelSerializer):
    """项目序列化器"""
    module_count = serializers.SerializerMethodField()
    app_count = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = "__all__"
        read_only_fields = ["creator", "modifier", "create_time", "update_time"]

    def get_module_count(self, obj):
        return obj.modules.filter(is_deleted=False).count()

    def get_app_count(self, obj):
        return obj.applications.filter(is_deleted=False).count()


class ProjectCreateSerializer(serializers.ModelSerializer):
    """项目创建序列化器"""
    class Meta:
        model = Project
        fields = ["name", "code", "description", "status", "sort"]


class ModuleSerializer(serializers.ModelSerializer):
    """模块序列化器"""
    project_name = serializers.CharField(source="project.name", read_only=True)
    app_count = serializers.SerializerMethodField()

    class Meta:
        model = Module
        fields = "__all__"
        read_only_fields = ["creator", "modifier", "create_time", "update_time"]

    def get_app_count(self, obj):
        return obj.applications.filter(is_deleted=False).count()


class ApplicationSerializer(serializers.ModelSerializer):
    """应用序列化器"""
    project_name = serializers.CharField(source="project.name", read_only=True)
    module_name = serializers.CharField(source="module.name", read_only=True)
    app_type_display = serializers.CharField(source="get_app_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Application
        fields = "__all__"
        read_only_fields = [
            "creator", "modifier", "create_time", "update_time",
            "git_url", "gitlab_project_id", "jenkins_ci_job", "harbor_project"
        ]


class ApplicationCreateSerializer(serializers.ModelSerializer):
    """应用创建序列化器"""
    class Meta:
        model = Application
        fields = [
            "project", "module", "name", "code", "description",
            "app_type", "build_branch", "dockerfile_path", "status", "sort"
        ]
```

#### 6.3.5 ViewSet规范

**必须**继承 `utils.custom_model_viewSet.CustomModelViewSet`：

```python
# backend/release/views/project.py
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from utils.custom_model_viewSet import CustomModelViewSet
from utils.permissions import HasButtonPermission
from ..models import Project, Module, Application
from ..serializers import (
    ProjectSerializer, ProjectCreateSerializer,
    ModuleSerializer, ApplicationSerializer
)
from ..filters import ProjectFilter


class ProjectViewSet(CustomModelViewSet):
    """项目管理"""
    queryset = Project.objects.filter(is_deleted=False)
    serializer_class = ProjectSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = ProjectFilter
    search_fields = ["name", "code"]
    ordering_fields = ["sort", "create_time"]
    enable_soft_delete = True

    # 动作到序列化器的映射
    action_serializers = {
        "create": ProjectCreateSerializer,
        "update": ProjectCreateSerializer,
    }

    def perform_create(self, serializer):
        """创建时自动设置创建人"""
        serializer.save(creator=self.request.user.username)

    def perform_update(self, serializer):
        """更新时自动设置修改人"""
        serializer.save(modifier=self.request.user.username)

    @action(detail=True, methods=["get"])
    def modules(self, request, pk=None):
        """获取项目下的模块列表"""
        project = self.get_object()
        modules = Module.objects.filter(project=project, is_deleted=False)
        serializer = ModuleSerializer(modules, many=True)
        return Response({"code": 0, "data": serializer.data})

    @action(detail=True, methods=["get"])
    def applications(self, request, pk=None):
        """获取项目下的应用列表"""
        project = self.get_object()
        applications = Application.objects.filter(
            project=project, is_deleted=False
        ).select_related("module")
        serializer = ApplicationSerializer(applications, many=True)
        return Response({"code": 0, "data": serializer.data})
```

#### 6.3.6 路由配置

```python
# backend/release/urls.py
from rest_framework.routers import DefaultRouter
from .views import ProjectViewSet, ModuleViewSet, ApplicationViewSet

router = DefaultRouter()
router.register(r"project", ProjectViewSet, basename="release-project")
router.register(r"module", ModuleViewSet, basename="release-module")
router.register(r"application", ApplicationViewSet, basename="release-application")

urlpatterns = router.urls
```

在 `backend/backend/urls.py` 中添加：

```python
urlpatterns = [
    # ... existing patterns ...
    path('api/admin/release/', include('release.urls')),
]
```

#### 6.3.7 权限控制

权限码格式：`{app_label}:{model_name}:{action}`

| 操作 | 权限码 |
|------|--------|
| 查询项目 | `release:project:query` |
| 创建项目 | `release:project:create` |
| 编辑项目 | `release:project:edit` |
| 删除项目 | `release:project:delete` |
| 创建应用 | `release:application:create` |
| 触发构建 | `release:application:build` |

在 `system_menu` 表中配置菜单和按钮权限：

```sql
-- 发布管理目录
INSERT INTO system_menu (name, path, component, type, auth_code, parent_id, status)
VALUES ('发布管理', '/release', 'LAYOUT', 'catalog', NULL, NULL, 1);

-- 项目管理菜单
INSERT INTO system_menu (name, path, component, type, auth_code, parent_id, status)
VALUES ('项目管理', 'project', 'release/project/index', 'menu', 'release:project:query', {发布管理ID}, 1);

-- 按钮权限
INSERT INTO system_menu (name, path, component, type, auth_code, parent_id, status)
VALUES 
('新增项目', '', '', 'button', 'release:project:create', {项目管理ID}, 1),
('编辑项目', '', '', 'button', 'release:project:edit', {项目管理ID}, 1),
('删除项目', '', '', 'button', 'release:project:delete', {项目管理ID}, 1);
```

### 6.4 前端开发规范

#### 6.4.1 目录结构

```
web/apps/web-antd/src/
├── api/release/                 # API接口定义
│   ├── project.ts               # 项目API
│   ├── module.ts                # 模块API
│   └── application.ts           # 应用API
├── views/release/               # 发布管理页面
│   ├── project/                 # 项目管理
│   │   ├── index.vue            # 列表页
│   │   ├── components/
│   │   │   ├── ProjectForm.vue  # 表单组件
│   │   │   └── ProjectTree.vue  # 树形组件
│   │   └── hooks/
│   │       └── useProject.ts    # 组合式函数
│   ├── module/                  # 模块管理
│   │   └── index.vue
│   └── application/             # 应用管理
│       ├── index.vue
│       └── components/
│           ├── AppForm.vue
│           └── BuildLog.vue
└── router/routes/modules/
    └── release.ts               # 路由配置
```

#### 6.4.2 API定义规范

```typescript
// web/apps/web-antd/src/api/release/project.ts
import { requestClient } from '#/api/request';

// 类型定义
export interface Project {
  id: number;
  name: string;
  code: string;
  description?: string;
  status: number;
  sort: number;
  module_count: number;
  app_count: number;
  create_time: string;
  update_time: string;
}

export interface ProjectListParams {
  page?: number;
  page_size?: number;
  name?: string;
  code?: string;
  status?: number;
}

// API方法
export const projectApi = {
  // 获取列表
  list: (params: ProjectListParams) =>
    requestClient.get<{ items: Project[]; total: number }>('/api/admin/release/project/', { params }),

  // 获取详情
  detail: (id: number) =>
    requestClient.get<Project>(`/api/admin/release/project/${id}/`),

  // 创建
  create: (data: Partial<Project>) =>
    requestClient.post<Project>('/api/admin/release/project/', data),

  // 更新
  update: (id: number, data: Partial<Project>) =>
    requestClient.put<Project>(`/api/admin/release/project/${id}/`, data),

  // 删除
  delete: (id: number) =>
    requestClient.delete(`/api/admin/release/project/${id}/`),

  // 获取模块列表
  modules: (id: number) =>
    requestClient.get(`/api/admin/release/project/${id}/modules/`),

  // 获取应用列表
  applications: (id: number) =>
    requestClient.get(`/api/admin/release/project/${id}/applications/`),
};
```

#### 6.4.3 页面组件规范

参考现有 `views/system/` 目录下的组件结构，使用：
- Ant Design Vue 组件
- Vben Admin 的表格、表单、弹窗组件
- TypeScript 类型定义

---

## 7. 数据模型设计

### 7.1 ER图

```
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│   Project   │       │   Module    │       │ Application │
├─────────────┤       ├─────────────┤       ├─────────────┤
│ id          │──┐    │ id          │──┐    │ id          │
│ name        │  │    │ project_id  │  │    │ module_id   │
│ code        │  │    │ name        │  │    │ project_id  │
│ description │  │    │ code        │  │    │ name        │
│ status      │  │    │ description │  │    │ code        │
│ ...         │  │    │ status      │  │    │ app_type    │
└─────────────┘  │    │ ...         │  │    │ git_url     │
                 │    └─────────────┘  │    │ status      │
                 │                     │    │ ...         │
                 │    ┌─────────────┐  │    └─────────────┘
                 │    │ ConfigPkg   │  │           │
                 │    ├─────────────┤  │           │
                 │    │ id          │  │           │
                 │    │ app_id      │──┘           │
                 │    │ version     │              │
                 │    │ file_path   │              │
                 │    │ sync_status │              │
                 │    │ ...         │              │
                 │    └─────────────┘              │
                 │           │                    │
                 │    ┌──────┴──────┐             │
                 │    │ SyncLog     │             │
                 │    ├─────────────┤             │
                 └────│ project_id  │             │
                      │ module_id   │             │
                      │ app_id      │◄────────────┘
                      │ sync_type   │
                      │ action      │
                      │ status      │
                      │ ...         │
                      └─────────────┘
```

### 7.2 数据表设计

#### 7.2.1 release_project（项目表）

```sql
CREATE TABLE `release_project` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `name` varchar(64) NOT NULL COMMENT '项目名称',
  `code` varchar(32) NOT NULL COMMENT '项目编码',
  `description` varchar(256) DEFAULT NULL COMMENT '项目描述',
  `gitlab_group_id` int DEFAULT NULL COMMENT 'GitLab Group ID',
  `status` tinyint NOT NULL DEFAULT '1' COMMENT '状态：0-禁用，1-启用',
  `sort` int DEFAULT '0' COMMENT '排序',
  `remark` varchar(256) DEFAULT NULL COMMENT '备注',
  `creator` varchar(64) DEFAULT NULL COMMENT '创建人',
  `modifier` varchar(64) DEFAULT NULL COMMENT '修改人',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `is_deleted` tinyint NOT NULL DEFAULT '0' COMMENT '是否删除',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_code` (`code`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='发布项目表';
```

#### 7.2.2 release_module（模块表）

```sql
CREATE TABLE `release_module` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `project_id` bigint NOT NULL COMMENT '所属项目ID',
  `name` varchar(64) NOT NULL COMMENT '模块名称',
  `code` varchar(32) NOT NULL COMMENT '模块编码',
  `description` varchar(256) DEFAULT NULL COMMENT '模块描述',
  `gitlab_subgroup_id` int DEFAULT NULL COMMENT 'GitLab Subgroup ID',
  `status` tinyint NOT NULL DEFAULT '1' COMMENT '状态：0-禁用，1-启用',
  `sort` int DEFAULT '0' COMMENT '排序',
  `remark` varchar(256) DEFAULT NULL COMMENT '备注',
  `creator` varchar(64) DEFAULT NULL COMMENT '创建人',
  `modifier` varchar(64) DEFAULT NULL COMMENT '修改人',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `is_deleted` tinyint NOT NULL DEFAULT '0' COMMENT '是否删除',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_project_code` (`project_id`, `code`),
  KEY `idx_project_id` (`project_id`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='发布模块表';
```

#### 7.2.3 release_application（应用表）

```sql
CREATE TABLE `release_application` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `project_id` bigint NOT NULL COMMENT '所属项目ID',
  `module_id` bigint NOT NULL COMMENT '所属模块ID',
  `name` varchar(64) NOT NULL COMMENT '应用名称',
  `code` varchar(32) NOT NULL COMMENT '应用编码',
  `description` varchar(256) DEFAULT NULL COMMENT '应用描述',
  `app_type` varchar(16) NOT NULL COMMENT '应用类型：java/nodejs/python/go/vue/react',
  `git_url` varchar(256) DEFAULT NULL COMMENT 'Git仓库地址',
  `gitlab_project_id` int DEFAULT NULL COMMENT 'GitLab Project ID',
  `jenkins_ci_job` varchar(128) DEFAULT NULL COMMENT 'Jenkins CI任务名称',
  `harbor_project` varchar(64) DEFAULT NULL COMMENT 'Harbor项目名称',
  `build_branch` varchar(64) DEFAULT 'main' COMMENT '构建分支',
  `dockerfile_path` varchar(128) DEFAULT './Dockerfile' COMMENT 'Dockerfile路径',
  `status` tinyint NOT NULL DEFAULT '1' COMMENT '状态：0-禁用，1-启用',
  `sort` int DEFAULT '0' COMMENT '排序',
  `remark` varchar(256) DEFAULT NULL COMMENT '备注',
  `creator` varchar(64) DEFAULT NULL COMMENT '创建人',
  `modifier` varchar(64) DEFAULT NULL COMMENT '修改人',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `is_deleted` tinyint NOT NULL DEFAULT '0' COMMENT '是否删除',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_module_code` (`module_id`, `code`),
  KEY `idx_project_id` (`project_id`),
  KEY `idx_module_id` (`module_id`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='发布应用表';
```

#### 7.2.4 release_config_package（配置包表）

```sql
CREATE TABLE `release_config_package` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `app_id` bigint NOT NULL COMMENT '关联应用ID',
  `version` varchar(32) NOT NULL COMMENT '配置包版本',
  `file_path` varchar(256) NOT NULL COMMENT '文件路径',
  `file_size` bigint NOT NULL COMMENT '文件大小（字节）',
  `checksum` varchar(64) NOT NULL COMMENT '文件校验和',
  `sync_status` tinyint NOT NULL DEFAULT '0' COMMENT '同步状态：0-待同步，1-同步中，2-已同步，3-失败',
  `sync_time` datetime DEFAULT NULL COMMENT '同步时间',
  `sync_message` varchar(512) DEFAULT NULL COMMENT '同步消息',
  `remark` varchar(256) DEFAULT NULL COMMENT '备注',
  `creator` varchar(64) DEFAULT NULL COMMENT '创建人',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `is_deleted` tinyint NOT NULL DEFAULT '0' COMMENT '是否删除',
  PRIMARY KEY (`id`),
  KEY `idx_app_id` (`app_id`),
  KEY `idx_sync_status` (`sync_status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='配置包表';
```

#### 7.2.5 release_sync_log（同步日志表）

```sql
CREATE TABLE `release_sync_log` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `config_package_id` bigint DEFAULT NULL COMMENT '配置包ID',
  `project_id` bigint DEFAULT NULL COMMENT '项目ID',
  `module_id` bigint DEFAULT NULL COMMENT '模块ID',
  `app_id` bigint DEFAULT NULL COMMENT '应用ID',
  `sync_type` varchar(16) NOT NULL COMMENT '同步类型：harbor/jenkins/ansible',
  `resource_name` varchar(128) NOT NULL COMMENT '资源名称',
  `action` varchar(16) NOT NULL COMMENT '操作：create/update/delete',
  `status` tinyint NOT NULL COMMENT '状态：0-失败，1-成功',
  `message` varchar(1024) DEFAULT NULL COMMENT '日志消息',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_config_package_id` (`config_package_id`),
  KEY `idx_app_id` (`app_id`),
  KEY `idx_sync_type` (`sync_type`),
  KEY `idx_create_time` (`create_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='同步日志表';
```

#### 7.2.6 release_template（模板表）

```sql
CREATE TABLE `release_template` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `name` varchar(64) NOT NULL COMMENT '模板名称',
  `code` varchar(32) NOT NULL COMMENT '模板编码',
  `template_type` varchar(16) NOT NULL COMMENT '模板类型：jenkinsfile/dockerfile/docker-compose',
  `app_type` varchar(16) DEFAULT NULL COMMENT '适用应用类型',
  `content` text NOT NULL COMMENT '模板内容',
  `description` varchar(256) DEFAULT NULL COMMENT '模板描述',
  `status` tinyint NOT NULL DEFAULT '1' COMMENT '状态：0-禁用，1-启用',
  `remark` varchar(256) DEFAULT NULL COMMENT '备注',
  `creator` varchar(64) DEFAULT NULL COMMENT '创建人',
  `modifier` varchar(64) DEFAULT NULL COMMENT '修改人',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `is_deleted` tinyint NOT NULL DEFAULT '0' COMMENT '是否删除',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_code` (`code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='发布模板表';
```

---

## 8. 接口设计

### 8.1 项目管理接口

#### 8.1.1 创建项目

- **URL**: `POST /api/admin/release/project/`
- **请求参数**:

```json
{
  "name": "大数据平台",
  "code": "bigdata-platform",
  "description": "企业大数据分析平台"
}
```

- **响应示例**:

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 1,
    "name": "大数据平台",
    "code": "bigdata-platform",
    "description": "企业大数据分析平台",
    "gitlab_group_id": 123,
    "status": 1,
    "create_time": "2026-03-01T10:00:00Z"
  }
}
```

### 8.2 模块管理接口

#### 8.2.1 创建模块

- **URL**: `POST /api/admin/release/module/`
- **请求参数**:

```json
{
  "project_id": 1,
  "name": "数据采集模块",
  "code": "data-collect",
  "description": "数据采集与接入模块"
}
```

### 8.3 应用管理接口

#### 8.3.1 创建应用

- **URL**: `POST /api/admin/release/application/`
- **请求参数**:

```json
{
  "project_id": 1,
  "module_id": 1,
  "name": "用户服务",
  "code": "user-service",
  "description": "用户管理服务",
  "app_type": "java",
  "build_branch": "main",
  "dockerfile_path": "./Dockerfile"
}
```

- **响应示例**:

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 1,
    "name": "用户服务",
    "code": "user-service",
    "git_url": "https://gitlab.example.com/bigdata-platform/data-collect/user-service.git",
    "gitlab_project_id": 456,
    "jenkins_ci_job": "bigdata-platform/data-collect/user-service-ci",
    "harbor_project": "bigdata-platform-data-collect",
    "config_package_id": 1,
    "create_time": "2026-03-01T10:00:00Z"
  }
}
```

#### 8.3.2 触发构建

- **URL**: `POST /api/admin/release/application/{id}/build/`
- **请求参数**:

```json
{
  "branch": "feature/user-auth",
  "parameters": {
    "BUILD_ENV": "dev",
    "VERSION": "v1.0.0"
  }
}
```

### 8.4 配置包接口

#### 8.4.1 生成配置包

- **URL**: `POST /api/admin/release/config-package/generate/`
- **请求参数**:

```json
{
  "app_ids": [1, 2, 3]
}
```

#### 8.4.2 查询同步状态

- **URL**: `GET /api/admin/release/config-package/{id}/sync-status/`

---

## 9. 配置包规范

### 9.1 配置包结构

```
config_package_v1.0.0_20260301.zip
├── manifest.json              # 清单文件
├── harbor/                    # Harbor配置
│   ├── projects.json          # 项目定义
│   └── replication_rules.json # 复制规则
├── jenkins/                   # Jenkins配置
│   └── jobs/                  # 任务定义
│       ├── app1-cd.json
│       └── app2-cd.json
└── ansible/                   # Ansible配置
    ├── inventory/
    │   └── app1.yaml
    └── playbooks/
        └── deploy.yaml
```

### 9.2 manifest.json 规范

```json
{
  "version": "1.0.0",
  "generated_at": "2026-03-01T10:00:00Z",
  "generated_by": "admin",
  "checksum": "sha256:abc123...",
  "apps": [
    {
      "id": 1,
      "project_code": "bigdata-platform",
      "module_code": "data-collect",
      "app_code": "user-service",
      "app_type": "java"
    }
  ],
  "resources": {
    "harbor": {
      "projects": 1,
      "replication_rules": 1
    },
    "jenkins": {
      "jobs": 1
    },
    "ansible": {
      "inventories": 1
    }
  }
}
```

### 9.3 Harbor配置规范

#### projects.json

```json
[
  {
    "project_name": "bigdata-platform-data-collect",
    "public": false,
    "metadata": {
      "project": "bigdata-platform",
      "module": "data-collect"
    }
  }
]
```

#### replication_rules.json

```json
[
  {
    "name": "sync-user-service",
    "src_registry": "internet-harbor",
    "dest_registry": "gov-harbor",
    "src_namespace": "bigdata-platform-data-collect",
    "dest_namespace": "bigdata-platform-data-collect",
    "filters": [
      {
        "type": "name",
        "value": "user-service"
      }
    ],
    "trigger": {
      "type": "event_based"
    }
  }
]
```

### 9.4 Jenkins配置规范

#### jobs/{app}-cd.json

```json
{
  "name": "user-service-cd",
  "folder": "bigdata-platform/data-collect",
  "type": "pipeline",
  "definition": {
    "script": "pipeline { ... }",
    "scm": null
  },
  "triggers": [
    {
      "type": "upstream",
      "config": {
        "upstream_projects": "user-service-ci"
      }
    }
  ],
  "parameters": [
    {
      "name": "IMAGE_TAG",
      "type": "string",
      "default": "latest"
    },
    {
      "name": "DEPLOY_ENV",
      "type": "choice",
      "choices": ["dev", "test", "prod"]
    }
  ]
}
```

### 9.5 Ansible配置规范

#### inventory/{app}.yaml

```yaml
all:
  children:
    bigdata-platform:
      children:
        data-collect:
          hosts:
            user-service-01:
              ansible_host: 192.168.1.10
              app_name: user-service
              app_port: 8080
              deploy_path: /opt/apps/user-service
```

---

## 10. 非功能性需求

### 10.1 性能需求

| 指标 | 目标值 |
|------|--------|
| 页面加载时间 | ≤2秒 |
| API响应时间 | ≤500ms（P95） |
| 应用创建时间 | ≤30秒 |
| 配置包生成时间 | ≤10秒 |
| 并发用户数 | ≥100 |

### 10.2 安全需求

| 需求 | 说明 |
|------|------|
| 身份认证 | 基于JWT的Token认证 |
| 权限控制 | 基于RBAC的细粒度权限控制 |
| 数据加密 | 敏感信息AES加密存储 |
| 审计日志 | 记录所有操作日志 |
| API安全 | 防SQL注入、XSS攻击 |

### 10.3 可用性需求

| 需求 | 说明 |
|------|------|
| 系统可用性 | ≥99.9% |
| 故障恢复时间 | ≤30分钟 |
| 数据备份 | 每日备份，保留30天 |
| 容灾方案 | 主备部署 |

### 10.4 兼容性需求

| 类型 | 说明 |
|------|------|
| 浏览器 | Chrome 90+、Firefox 88+、Edge 90+ |
| GitLab | 14.0+ |
| Jenkins | 2.300+ |
| Harbor | 2.0+ |

---

## 11. 开发计划

### 11.1 里程碑

| 阶段 | 内容 | 预计工期 |
|------|------|----------|
| **M1: 基础框架** | 项目/模块/应用CRUD、数据库设计 | 1周 |
| **M2: GitLab集成** | GitLab API集成、Group/Subgroup/Repository创建 | 1周 |
| **M3: Jenkins集成** | Jenkins API集成、CI/CD任务创建 | 1周 |
| **M4: Harbor集成** | Harbor API集成、项目和机器人账号创建 | 1周 |
| **M5: 配置包** | 配置包生成、上传、下载 | 1周 |
| **M6: 同步机制** | 政务网同步脚本、定时任务 | 1周 |
| **M7: 权限控制** | 项目级权限、审批流程 | 1周 |
| **M8: 测试上线** | 单元测试、集成测试、UAT测试 | 1周 |

### 11.2 迭代计划

#### Sprint 1 (Week 1-2)

- [ ] 数据库表创建
- [ ] Project/Module/Application 后端API
- [ ] 前端页面开发
- [ ] GitLab API集成

#### Sprint 2 (Week 3-4)

- [ ] Jenkins API集成
- [ ] Harbor API集成
- [ ] 应用创建完整流程

#### Sprint 3 (Week 5-6)

- [ ] 配置包生成
- [ ] 政务网同步脚本
- [ ] 定时任务配置

#### Sprint 4 (Week 7-8)

- [ ] 权限控制
- [ ] 审批流程
- [ ] 测试和修复

---

## 12. 风险与应对

### 12.1 技术风险

| 风险 | 影响 | 概率 | 应对措施 |
|------|------|------|----------|
| GitLab API版本兼容性 | 高 | 中 | 封装适配层，支持多版本API |
| 网闸传输失败 | 高 | 低 | 增加重试机制，记录详细日志 |
| 并发创建冲突 | 中 | 中 | 使用分布式锁，乐观锁控制 |
| 配置包解析失败 | 中 | 低 | 增加格式校验，异常处理 |

### 12.2 业务风险

| 风险 | 影响 | 概率 | 应对措施 |
|------|------|------|----------|
| 命名冲突 | 中 | 高 | 建立命名规范检查，提前预警 |
| 权限配置错误 | 高 | 中 | 权限预览功能，审批流程 |
| 资源清理困难 | 中 | 中 | 软删除机制，定期清理任务 |

### 12.3 依赖风险

| 风险 | 影响 | 概率 | 应对措施 |
|------|------|------|----------|
| GitLab服务不可用 | 高 | 低 | 健康检查，降级处理 |
| Jenkins服务不可用 | 高 | 低 | 健康检查，降级处理 |
| Harbor服务不可用 | 高 | 低 | 健康检查，降级处理 |
| 网闸故障 | 高 | 低 | 人工介入，应急预案 |

---

## 附录

### A. 状态码定义

| 状态码 | 说明 |
|--------|------|
| 0 | 禁用/失败/待处理 |
| 1 | 启用/成功 |
| 2 | 处理中/同步中 |
| 3 | 错误/失败 |

### B. 应用类型

| 类型 | 说明 | 构建工具 |
|------|------|----------|
| java | Java应用 | Maven/Gradle |
| nodejs | Node.js应用 | npm/yarn |
| python | Python应用 | pip |
| go | Go应用 | go mod |
| vue | Vue前端应用 | npm/yarn |
| react | React前端应用 | npm/yarn |

### C. 参考文档

- [GitLab API文档](https://docs.gitlab.com/ee/api/)
- [Jenkins API文档](https://www.jenkins.io/doc/book/using/remote-access-api/)
- [Harbor API文档](https://github.com/goharbor/harbor/blob/main/docs/swagger.yaml)

---

**文档变更历史**

| 版本 | 日期 | 作者 | 变更说明 |
|------|------|------|----------|
| v1.0 | 2026-03-01 | DevOps团队 | 初始版本 |
