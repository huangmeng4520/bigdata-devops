---
name: cicd-template-system-development
overview: 基于 PRD 文档开发 CI/CD 模板系统，包括流水线模板管理、应用 CI/CD 配置、多环境策略、CD 配置导出等核心功能模块，涉及后端 Django 模型、API 接口、服务层和前端 Vue3 页面开发。
design:
  architecture:
    framework: vue
    component: tdesign
  styleKeywords:
    - Enterprise
    - Professional
    - Functional
  fontSystem:
    fontFamily: PingFang SC
    heading:
      size: 20px
      weight: 600
    subheading:
      size: 16px
      weight: 500
    body:
      size: 14px
      weight: 400
  colorSystem:
    primary:
      - "#0052D9"
      - "#366EF4"
    background:
      - "#F3F5F7"
      - "#FFFFFF"
    text:
      - "#1D2129"
      - "#4E5969"
      - "#86909C"
    functional:
      - "#00A870"
      - "#E34D59"
      - "#ED7B2F"
todos:
  - id: create-models
    content: 创建 6 个新数据模型并生成数据库迁移
    status: completed
  - id: create-template-api
    content: 实现模板管理后端 API（CRUD + 版本管理）
    status: completed
    dependencies:
      - create-models
  - id: create-app-config-api
    content: 实现应用配置后端 API（CI/CD 配置 + 版本管理）
    status: completed
    dependencies:
      - create-models
  - id: create-strategy-export-api
    content: 实现环境策略和 CD 导出后端 API
    status: completed
    dependencies:
      - create-models
  - id: create-template-frontend
    content: 开发模板管理前端页面（列表、表单、版本管理）
    status: completed
    dependencies:
      - create-template-api
  - id: create-app-config-frontend
    content: 开发应用 CI/CD 配置前端页面（环境配置、版本历史）
    status: completed
    dependencies:
      - create-app-config-api
  - id: create-export-frontend
    content: 开发环境策略和 CD 导出前端页面
    status: completed
    dependencies:
      - create-strategy-export-api
  - id: setup-routes-menu
    content: 配置前端路由和菜单
    status: completed
    dependencies:
      - create-template-frontend
      - create-app-config-frontend
      - create-export-frontend
---

## 产品概述

CI/CD 模板系统与多环境流水线管理功能，支持多语言模板管理、应用级别 CI/CD 配置、多环境策略及跨网络 CD 配置导出。

## 核心功能

### 1. 模板管理模块

- CI/CD 模板 CRUD 管理（支持 Java、Python、Node.js、Go、.NET 等多语言）
- 模板版本管理（语义化版本号、版本历史、设置最新版本）
- 模板变量定义（支持 select、string、boolean、secret 类型）
- 模板阶段配置（Checkout、Build、Test、SonarQube、DockerBuild、HarborPush 等）

### 2. 应用配置模块

- 应用 CI/CD 配置管理（关联模板、设置变量值、阶段配置）
- 配置版本历史与回滚
- Jenkinsfile 生成与预览
- 自动应用到 Jenkins

### 3. 环境策略管理

- 多环境策略配置（开发、测试、准生产、生产）
- CI/CD 合并/分离模式支持
- 审批流程配置
- 自动部署开关

### 4. CD 配置导出

- 导出 Jenkinsfile CD 流水线
- 导出 Ansible Playbook 部署剧本
- 导出部署配置 JSON/YAML
- 导出完整配置包（ZIP 格式）
- 导出历史记录与下载

### 5. 命名规范验证 API

- 验证项目/模块/应用命名是否符合规范
- 生成标准化资源名称（GitLab、Harbor、Jenkins、Ansible）

## 技术栈

### 后端

- **框架**: Django REST Framework（复用现有架构）
- **数据库**: MySQL（通过 Django ORM）
- **任务队列**: Celery（复用现有异步任务机制）
- **过滤**: django-filter（复用现有过滤器模式）

### 前端

- **框架**: Vue 3 + TypeScript
- **UI 组件**: Ant Design Vue
- **表格组件**: Vxe-table
- **表单组件**: Vben Form
- **状态管理**: 复用现有模式

## 技术架构

### 后端分层架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        API Layer (Views)                        │
│  PipelineTemplateViewSet | ApplicationPipelineConfigViewSet    │
│  EnvironmentStrategyViewSet | CDConfigExportViewSet             │
├─────────────────────────────────────────────────────────────────┤
│                     Serializer Layer                            │
│  数据验证、序列化/反序列化、嵌套关系处理                           │
├─────────────────────────────────────────────────────────────────┤
│                      Service Layer                              │
│  PipelineTemplateService | JenkinsfileGenerator                │
│  AnsibleGenerator | CDExportService                            │
├─────────────────────────────────────────────────────────────────┤
│                      Model Layer                                │
│  PipelineTemplate | PipelineTemplateVersion                    │
│  ApplicationPipelineConfig | ApplicationPipelineVersion        │
│  EnvironmentStrategy | CDConfigExport                          │
└─────────────────────────────────────────────────────────────────┘
```

### 前端组件架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        Views (Pages)                            │
│  PipelineTemplateList | ApplicationPipelineConfig              │
│  EnvironmentStrategyList | CDConfigExport                      │
├─────────────────────────────────────────────────────────────────┤
│                     Components (Modules)                        │
│  TemplateForm | VersionHistory | VariableEditor                │
│  StageConfig | JenkinsfilePreview | ExportDialog               │
├─────────────────────────────────────────────────────────────────┤
│                        API Layer                                │
│  pipelineTemplateApi | applicationPipelineApi                  │
│  environmentStrategyApi | cdExportApi                          │
└─────────────────────────────────────────────────────────────────┘
```

## 实现方案

### 1. 数据模型设计

遵循现有 CoreModel 基类模式，新增 6 个模型：

- PipelineTemplate：流水线模板主表
- PipelineTemplateVersion：模板版本表（支持语义化版本）
- ApplicationPipelineConfig：应用配置表（unique: application + config_type + environment）
- ApplicationPipelineVersion：配置版本快照表
- EnvironmentStrategy：环境策略表
- CDConfigExport：CD 配置导出记录表

### 2. Jenkinsfile 生成引擎

- 变量替换： `${variableName}` → 实际值
- 阶段控制：根据 stages_config 启用/禁用阶段
- 内容合并：模板内容 + 自定义内容

### 3. Ansible 配置生成

- 生成 deploy-docker.yml 部署剧本
- 生成 inventory 主机清单
- 生成 deploy-config.json 部署配置

### 4. 关键性能考虑

- 模板列表查询：使用 select_related 预加载最新版本
- 配置版本历史：添加索引 (config_id, version)
- 导出内容存储：使用 LONGTEXT 存储大文本

## 目录结构

```
backend/release/
├── models.py                    # [MODIFY] 新增 6 个模型
├── serializers.py               # [MODIFY] 新增序列化器
├── filters.py                   # [MODIFY] 新增过滤器
├── urls.py                      # [MODIFY] 新增路由注册
├── views/
│   ├── __init__.py              # [MODIFY] 导出新视图
│   ├── pipeline_template.py     # [NEW] 模板管理视图
│   ├── application_pipeline.py  # [NEW] 应用配置视图
│   ├── environment_strategy.py  # [NEW] 环境策略视图
│   └── cd_export.py             # [NEW] CD 导出视图
└── services/
    ├── __init__.py              # [MODIFY] 导出新服务
    ├── pipeline_service.py      # [NEW] 模板管理服务
    ├── jenkinsfile_generator.py # [NEW] Jenkinsfile 生成引擎
    └── ansible_generator.py     # [NEW] Ansible 配置生成

web/apps/web-antd/src/
├── api/release/
│   ├── index.ts                 # [MODIFY] 导出新 API
│   ├── pipeline-template.ts     # [NEW] 模板管理 API
│   ├── application-pipeline.ts  # [NEW] 应用配置 API
│   ├── environment-strategy.ts  # [NEW] 环境策略 API
│   └── cd-export.ts             # [NEW] CD 导出 API
├── views/release/
│   ├── pipeline-template/       # [NEW] 模板管理页面
│   │   ├── index.vue
│   │   ├── data.ts
│   │   └── modules/
│   │       ├── form.vue
│   │       └── version-form.vue
│   ├── application-pipeline/    # [NEW] 应用配置页面
│   │   ├── index.vue
│   │   ├── data.ts
│   │   └── modules/
│   │       ├── config-form.vue
│   │       └── version-history.vue
│   ├── environment-strategy/    # [NEW] 环境策略页面
│   │   ├── index.vue
│   │   ├── data.ts
│   │   └── modules/
│   │       └── form.vue
│   └── cd-export/               # [NEW] CD 导出页面
│       ├── index.vue
│       ├── data.ts
│       └── modules/
│           └── export-dialog.vue
└── router/routes/modules/
    └── release.ts               # [NEW] 发布模块路由配置
```

## 设计风格

采用企业级管理系统设计风格，强调功能清晰、操作便捷。使用 TDesign Vue 组件库保持与现有系统一致性。

## 页面规划

### 1. 模板管理页面

- 顶部搜索筛选栏（类型、语言、关键字）
- 模板列表表格（类型标签、语言标签、当前版本、操作按钮）
- 模板编辑弹窗（基本信息、模板内容编辑器、变量定义表格、阶段配置）

### 2. 应用 CI/CD 配置页面

- 环境切换标签页（开发/测试/准生产/生产）
- CI 配置卡片（模板选择、变量配置、阶段开关）
- CD 配置卡片（部署模板、环境策略、审批配置）
- 版本历史侧边栏

### 3. CD 配置导出页面

- 导出配置表单（目标环境、导出格式）
- 内容预览区域（代码高亮显示）
- 导出历史列表

## 交互设计

- 模板内容编辑器：代码高亮、变量插入提示
- 变量配置：动态表单根据变量类型显示不同输入组件
- 版本对比：支持查看两个版本的差异
- 导出预览：实时预览生成的配置内容

## SubAgent

- **code-explorer**
- Purpose: 在开发过程中探索现有代码模式和组件实现
- Expected outcome: 确保新代码遵循项目现有规范和模式