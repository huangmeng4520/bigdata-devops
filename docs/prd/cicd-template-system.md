# CI/CD 模板系统与多环境流水线管理 PRD

## 文档信息

| 项目 | 内容 |
|------|------|
| 版本 | v1.0 |
| 创建日期 | 2026-03-01 |
| 作者 | DevOps Team |
| 状态 | 草稿 |

---

## 1. 背景与目标

### 1.1 背景

当前系统已完成基础骨架开发，支持：
- 项目/模块/应用三级管理
- GitLab Group/Subgroup/Repository 自动创建
- Jenkins Folder 自动创建
- Harbor Project 自动创建

但在 CI/CD 流水线管理方面存在以下痛点：
1. 缺乏针对不同编程语言的标准化模板
2. 无法灵活定制不同环境的流水线阶段
3. 模板和应用配置缺乏版本管理
4. 跨网络（互联网/政务网）的 CI/CD 协同困难

### 1.2 目标

构建完整的 CI/CD 模板系统，实现：
- 多语言模板支持与版本管理
- 应用级别的 CI/CD 配置自定义
- 多环境（测试/准生产/生产）流水线策略
- 跨网络环境的 CD 配置导出与同步

---

## 2. 系统架构

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                        DevOps 管理平台                               │
├─────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │  模板管理     │  │  应用配置    │  │   环境策略管理            │  │
│  │  - CI 模板   │  │  - CI 配置   │  │   - 测试环境策略          │  │
│  │  - CD 模板   │  │  - CD 配置   │  │   - 准生产环境策略        │  │
│  │  - 版本管理   │  │  - 版本管理   │  │   - 生产环境策略          │  │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘  │
├─────────────────────────────────────────────────────────────────────┤
│                         流水线引擎                                   │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  测试环境                    │  准生产/生产环境              │   │
│  │  CI + CD 合并流水线          │  CI (互联网) + CD (政务网)    │   │
│  └─────────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────────┤
│      互联网 Jenkins          │           政务网 Jenkins            │
│      (CI 流水线)             │           (CD 流水线)               │
│      ←───────────────────────┼─────────────────────────────────→   │
│           配置导出/导入       │         手动同步                    │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 网络拓扑

```
┌─────────────────────────────────────────────────────────────────┐
│                         互联网区域                               │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐ │
│  │   GitLab    │    │  Jenkins    │    │   DevOps 平台       │ │
│  │  (代码仓库)  │←──→│  (CI 执行)   │←──→│   (管理中心)        │ │
│  └─────────────┘    └─────────────┘    └─────────────────────┘ │
│                            ↓                                    │
│                     Harbor (镜像仓库)                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                    ══════════╪══════════
                    物理隔离/网闸
                    ══════════╪══════════
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                         政务网区域                               │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐ │
│  │   Harbor    │    │  Jenkins    │    │   Kubernetes        │ │
│  │  (镜像同步)  │←──→│  (CD 执行)   │←──→│   (运行环境)        │ │
│  └─────────────┘    └─────────────┘    └─────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. 数据模型设计

### 3.1 模板相关模型

#### 3.1.1 PipelineTemplate (流水线模板)

```python
class PipelineTemplate(CoreModel):
    """流水线模板"""
    name = models.CharField(max_length=128, verbose_name="模板名称")
    code = models.CharField(max_length=64, unique=True, verbose_name="模板编码")
    template_type = models.CharField(max_length=20, choices=[
        ('ci', 'CI 模板'),
        ('cd', 'CD 模板'),
    ], verbose_name="模板类型")
    language = models.CharField(max_length=32, verbose_name="编程语言")
    language_version = models.CharField(max_length=32, blank=True, verbose_name="语言版本")
    description = models.TextField(blank=True, verbose_name="描述")
    framework = models.CharField(max_length=64, blank=True, verbose_name="框架")
    is_official = models.BooleanField(default=False, verbose_name="官方模板")
    status = models.BooleanField(default=True, verbose_name="状态")
```

#### 3.1.2 PipelineTemplateVersion (模板版本)

```python
class PipelineTemplateVersion(CoreModel):
    """模板版本"""
    template = models.ForeignKey(PipelineTemplate, on_delete=models.CASCADE, related_name='versions')
    version = models.CharField(max_length=32, verbose_name="版本号")  # 如 1.0.0
    content = models.TextField(verbose_name="模板内容 (Jenkinsfile)")
    variables = models.JSONField(default=dict, verbose_name="模板变量定义")
    stages = models.JSONField(default=list, verbose_name="阶段定义")
    change_log = models.TextField(blank=True, verbose_name="变更日志")
    is_latest = models.BooleanField(default=False, verbose_name="是否最新版本")
    status = models.BooleanField(default=True, verbose_name="状态")

    class Meta:
        unique_together = ['template', 'version']
```

### 3.2 应用配置模型

#### 3.2.1 ApplicationPipelineConfig (应用流水线配置)

```python
class ApplicationPipelineConfig(CoreModel):
    """应用流水线配置"""
    application = models.ForeignKey('Application', on_delete=models.CASCADE, related_name='pipeline_configs')
    config_type = models.CharField(max_length=20, choices=[
        ('ci', 'CI 配置'),
        ('cd', 'CD 配置'),
    ], verbose_name="配置类型")
    environment = models.CharField(max_length=32, choices=[
        ('dev', '开发环境'),
        ('test', '测试环境'),
        ('staging', '准生产环境'),
        ('production', '生产环境'),
    ], verbose_name="环境")
    template = models.ForeignKey(PipelineTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    template_version = models.ForeignKey(PipelineTemplateVersion, on_delete=models.SET_NULL, null=True, blank=True)
    custom_content = models.TextField(blank=True, verbose_name="自定义内容")
    variables = models.JSONField(default=dict, verbose_name="变量值")
    stages_config = models.JSONField(default=list, verbose_name="阶段配置")
    is_active = models.BooleanField(default=True, verbose_name="是否启用")
    
    class Meta:
        unique_together = ['application', 'config_type', 'environment']
```

#### 3.2.2 ApplicationPipelineVersion (应用配置版本)

```python
class ApplicationPipelineVersion(CoreModel):
    """应用配置版本"""
    config = models.ForeignKey(ApplicationPipelineConfig, on_delete=models.CASCADE, related_name='versions')
    version = models.IntegerField(verbose_name="版本号")
    content = models.TextField(verbose_name="生成的 Jenkinsfile")
    variables_snapshot = models.JSONField(default=dict, verbose_name="变量快照")
    stages_snapshot = models.JSONField(default=list, verbose_name="阶段快照")
    generated_at = models.DateTimeField(auto_now_add=True, verbose_name="生成时间")
    generated_by = models.CharField(max_length=64, verbose_name="生成人")
    
    class Meta:
        unique_together = ['config', 'version']
```

### 3.3 环境策略模型

#### 3.3.1 EnvironmentStrategy (环境策略)

```python
class EnvironmentStrategy(CoreModel):
    """环境策略"""
    name = models.CharField(max_length=64, verbose_name="策略名称")
    code = models.CharField(max_length=32, unique=True, verbose_name="策略编码")
    environment = models.CharField(max_length=32, verbose_name="环境")
    pipeline_mode = models.CharField(max_length=32, choices=[
        ('integrated', 'CI/CD 合并'),
        ('separated', 'CI/CD 分离'),
    ], verbose_name="流水线模式")
    ci_jenkins = models.CharField(max_length=128, blank=True, verbose_name="CI Jenkins 标识")
    cd_jenkins = models.CharField(max_length=128, blank=True, verbose_name="CD Jenkins 标识")
    requires_approval = models.BooleanField(default=False, verbose_name="需要审批")
    auto_deploy = models.BooleanField(default=False, verbose_name="自动部署")
    description = models.TextField(blank=True, verbose_name="描述")
    is_default = models.BooleanField(default=False, verbose_name="默认策略")
```

### 3.4 CD 配置导出模型

#### 3.4.1 CDConfigExport (CD 配置导出)

```python
class CDConfigExport(CoreModel):
    """CD 配置导出记录"""
    application = models.ForeignKey('Application', on_delete=models.CASCADE)
    environment = models.CharField(max_length=32, verbose_name="环境")
    version = models.IntegerField(verbose_name="配置版本")
    export_format = models.CharField(max_length=20, choices=[
        ('jenkinsfile', 'Jenkinsfile'),
        ('json', 'JSON 配置'),
        ('yaml', 'YAML 配置'),
        ('zip', '压缩包'),
    ], verbose_name="导出格式")
    content = models.TextField(verbose_name="导出内容")
    file_path = models.CharField(max_length=512, blank=True, verbose_name="文件路径")
    exported_by = models.CharField(max_length=64, verbose_name="导出人")
    download_count = models.IntegerField(default=0, verbose_name="下载次数")
    
    class Meta:
        ordering = ['-create_time']
```

---

## 4. 标准化命名规范

### 4.1 命名规范概述

为保证 CI/CD 流程能够高度自动化运行，所有资源必须遵循统一的命名规范。**项目（project）和模块（module）命名禁止包含 `-` 字符**，以确保跨系统兼容性。

### 4.2 资源命名规则

| 资源类型 | 命名格式 | 示例 | 说明 |
|----------|----------|------|------|
| GitLab Group | `<project>` | `medicare` | 项目编码，不含 `-` |
| GitLab Subgroup | `<module>` | `payment` | 模块编码，不含 `-` |
| GitLab Repository | `<app>` | `service` | 应用编码 |
| 互联网 Harbor 项目 | `<project>-<module>` | `medicare-payment` | 用 `-` 连接项目与模块 |
| 镜像名 | `<app>` | `service` | 与应用编码一致 |
| 镜像标签 | `<version>-<environment>` | `1.2.3-uat` | 版本号 + 环境标识 |
| 政务网 Jenkins Job | `<project>/<module>/<app>/<env>` | `medicare/payment/service/uat` | 完整路径格式 |
| Ansible Inventory | `inventory/<project>/<module>/<app>/<env>` | `inventory/medicare/payment/service/uat` | 目录结构格式 |

### 4.3 命名约束规则

#### 4.3.1 项目（Project）命名规则

```python
# 项目命名验证规则
PROJECT_NAME_RULES = {
    "pattern": r"^[a-z][a-z0-9_]*$",  # 小写字母开头，仅允许小写字母、数字、下划线
    "forbidden_chars": ["-"],         # 禁止字符
    "min_length": 2,
    "max_length": 32,
    "examples": {
        "valid": ["medicare", "ehr_system", "ops_platform"],
        "invalid": ["medicare-app", "EHR", "123project"]
    }
}
```

#### 4.3.2 模块（Module）命名规则

```python
# 模块命名验证规则
MODULE_NAME_RULES = {
    "pattern": r"^[a-z][a-z0-9_]*$",  # 小写字母开头，仅允许小写字母、数字、下划线
    "forbidden_chars": ["-"],         # 禁止字符
    "min_length": 2,
    "max_length": 32,
    "examples": {
        "valid": ["payment", "user_center", "report"],
        "invalid": ["payment-svc", "UserCenter", "1module"]
    }
}
```

#### 4.3.3 应用（Application）命名规则

```python
# 应用命名验证规则
APP_NAME_RULES = {
    "pattern": r"^[a-z][a-z0-9_-]*$",  # 小写字母开头，允许小写字母、数字、下划线、连字符
    "min_length": 2,
    "max_length": 64,
    "examples": {
        "valid": ["service", "api-gateway", "web_frontend"],
        "invalid": ["Service", "1api", ""]
    }
}
```

### 4.4 环境标识规范

| 环境 | 标识 | 全称 | 说明 |
|------|------|------|------|
| 开发环境 | `dev` | development | 开发调试环境 |
| 测试环境 | `test` | testing | 功能测试环境 |
| UAT 环境 | `uat` | user acceptance testing | 用户验收测试环境 |
| 准生产环境 | `staging` | staging | 预发布环境 |
| 生产环境 | `prod` | production | 正式生产环境 |

### 4.5 版本号规范

采用语义化版本号（Semantic Versioning）：`<major>.<minor>.<patch>`

```
版本号格式: MAJOR.MINOR.PATCH

示例:
- 1.0.0  初始版本
- 1.1.0  新增功能
- 1.1.1  Bug 修复
- 2.0.0  重大变更

镜像标签格式: <version>-<environment>

示例:
- 1.2.3-dev      开发环境版本
- 1.2.3-test     测试环境版本
- 1.2.3-uat      UAT 环境版本
- 1.2.3-prod     生产环境版本
- 1.2.3-prod-rc1 生产环境发布候选
```

### 4.6 资源命名示例

#### 4.6.1 完整示例：医疗保障系统

```
项目信息:
- 项目编码: medicare
- 项目名称: 医疗保障系统

模块信息:
- 模块编码: payment
- 模块名称: 支付结算模块

应用信息:
- 应用编码: service
- 应用名称: 支付服务
- 版本号: 1.2.3
- 目标环境: uat

生成的资源命名:
├── GitLab
│   ├── Group: medicare
│   ├── Subgroup: medicare/payment
│   └── Repository: medicare/payment/service
├── Harbor (互联网)
│   ├── Project: medicare-payment
│   ├── Image: medicare-payment/service
│   └── Tag: 1.2.3-uat
├── Jenkins (政务网)
│   └── Job: medicare/payment/service/uat
└── Ansible
    └── Inventory: inventory/medicare/payment/service/uat
```

#### 4.6.2 多环境部署示例

```
应用: service
版本: 1.2.3

开发环境 (dev):
- 镜像: harbor.com/medicare-payment/service:1.2.3-dev
- Jenkins Job: medicare/payment/service/dev
- Inventory: inventory/medicare/payment/service/dev

测试环境 (test):
- 镜像: harbor.com/medicare-payment/service:1.2.3-test
- Jenkins Job: medicare/payment/service/test
- Inventory: inventory/medicare/payment/service/test

UAT 环境 (uat):
- 镜像: harbor.com/medicare-payment/service:1.2.3-uat
- Jenkins Job: medicare/payment/service/uat
- Inventory: inventory/medicare/payment/service/uat

生产环境 (prod):
- 镜像: harbor.com/medicare-payment/service:1.2.3-prod
- Jenkins Job: medicare/payment/service/prod
- Inventory: inventory/medicare/payment/service/prod
```

### 4.7 命名验证 API

```python
# API: 验证命名是否符合规范
POST /api/admin/release/validate-naming/

Request:
{
    "type": "project",  # project, module, app
    "name": "medicare-payment"
}

Response:
{
    "valid": false,
    "errors": [
        {
            "field": "name",
            "message": "项目名称不能包含 '-' 字符",
            "rule": "forbidden_chars"
        }
    ],
    "suggestion": "medicare_payment"
}

# API: 生成标准化名称
POST /api/admin/release/generate-names/

Request:
{
    "project": "medicare",
    "module": "payment",
    "app": "service",
    "version": "1.2.3",
    "environment": "uat"
}

Response:
{
    "gitlab": {
        "group": "medicare",
        "subgroup": "medicare/payment",
        "repository": "medicare/payment/service"
    },
    "harbor": {
        "project": "medicare-payment",
        "image": "medicare-payment/service",
        "tag": "1.2.3-uat"
    },
    "jenkins": {
        "folder": "medicare/payment",
        "job": "medicare/payment/service/uat"
    },
    "ansible": {
        "inventory": "inventory/medicare/payment/service/uat"
    }
}
```

---

## 5. 模板系统设计

### 5.1 支持的语言与框架

#### 5.1.1 CI 模板分类

| 语言 | 框架 | 构建工具 | 模板编码 |
|------|------|----------|----------|
| Java | Spring Boot | Maven | `ci-java-springboot-maven` |
| Java | Spring Boot | Gradle | `ci-java-springboot-gradle` |
| Java | Spring Cloud | Maven | `ci-java-springcloud-maven` |
| Python | Django | pip | `ci-python-django` |
| Python | Flask | pip | `ci-python-flask` |
| Python | FastAPI | pip | `ci-python-fastapi` |
| Node.js | Vue | npm/yarn/pnpm | `ci-nodejs-vue` |
| Node.js | React | npm/yarn/pnpm | `ci-nodejs-react` |
| Node.js | Next.js | npm/yarn/pnpm | `ci-nodejs-nextjs` |
| Go | Gin | go mod | `ci-go-gin` |
| Go | Beego | go mod | `ci-go-beego` |
| .NET Core | ASP.NET | dotnet | `ci-dotnet-aspnet` |

#### 5.1.2 CD 模板分类

政务网环境使用 Ansible 进行 Docker 镜像部署，模板分类如下：

| 部署类型 | 部署方式 | 模板编码 | 说明 |
|----------|----------|----------|------|
| Docker 单机部署 | Ansible | `cd-ansible-docker` | 单机 Docker 容器部署 |
| Docker Compose 部署 | Ansible | `cd-ansible-compose` | 多容器编排部署 |
| Docker Swarm 部署 | Ansible | `cd-ansible-swarm` | Swarm 集群部署 |
| Kubernetes 部署 | Ansible | `cd-ansible-k8s` | 通过 Ansible 调用 kubectl |
| 虚拟机脚本部署 | Ansible | `cd-ansible-script` | 传统脚本部署方式 |

**Ansible 部署优势：**
- 统一的配置管理和部署流程
- 支持批量部署到多台服务器
- 幂等性操作，可重复执行
- 丰富的模块支持（docker_container、docker_compose 等）
- 完善的错误处理和回滚机制

### 5.2 模板变量系统

#### 5.2.1 变量定义格式

```json
{
  "variables": [
    {
      "name": "BUILD_TOOL",
      "type": "select",
      "label": "构建工具",
      "default": "maven",
      "options": ["maven", "gradle"],
      "required": true
    },
    {
      "name": "JAVA_VERSION",
      "type": "select",
      "label": "Java 版本",
      "default": "17",
      "options": ["8", "11", "17", "21"],
      "required": true
    },
    {
      "name": "MAVEN_OPTS",
      "type": "string",
      "label": "Maven 参数",
      "default": "-Xmx1024m",
      "required": false
    },
    {
      "name": "SKIP_TESTS",
      "type": "boolean",
      "label": "跳过测试",
      "default": false,
      "required": false
    },
    {
      "name": "DEPLOY_TARGET",
      "type": "string",
      "label": "部署目标服务器",
      "default": "",
      "required": false,
      "secret": true
    }
  ]
}
```

#### 5.2.2 模板变量引用

在 Jenkinsfile 模板中使用 `${variableName}` 引用变量：

```groovy
pipeline {
    agent {
        kubernetes {
            yaml '''
apiVersion: v1
kind: Pod
spec:
  containers:
  - name: maven
    image: maven:${MAVEN_VERSION}
    command: ['sleep', '99d']
'''
        }
    }
    
    environment {
        JAVA_HOME = '/usr/lib/jvm/java-${JAVA_VERSION}'
        MAVEN_OPTS = '${MAVEN_OPTS}'
    }
    
    stages {
        stage('Build') {
            steps {
                sh 'mvn clean package ${SKIP_TESTS ? "-DskipTests" : ""}'
            }
        }
    }
}
```

### 5.3 模板阶段定义

```json
{
  "stages": [
    {
      "name": "Checkout",
      "alias": "代码检出",
      "required": true,
      "order": 1,
      "editable": false
    },
    {
      "name": "Build",
      "alias": "构建",
      "required": true,
      "order": 2,
      "editable": true,
      "configurable": ["build_command", "build_args"]
    },
    {
      "name": "Test",
      "alias": "测试",
      "required": false,
      "order": 3,
      "editable": true,
      "configurable": ["test_command", "coverage_threshold"]
    },
    {
      "name": "SonarQube",
      "alias": "代码质量",
      "required": false,
      "order": 4,
      "editable": true,
      "configurable": ["enabled", "quality_gate"]
    },
    {
      "name": "DockerBuild",
      "alias": "镜像构建",
      "required": true,
      "order": 5,
      "editable": true,
      "configurable": ["dockerfile_path", "image_tag"]
    },
    {
      "name": "HarborPush",
      "alias": "镜像推送",
      "required": true,
      "order": 6,
      "editable": true,
      "configurable": ["registry", "project"]
    }
  ]
}
```

---

## 6. 多环境策略设计

### 6.1 环境策略配置

#### 6.1.1 测试环境策略

```yaml
strategy:
  name: "测试环境集成策略"
  code: "test-integrated"
  environment: "test"
  pipeline_mode: "integrated"  # CI/CD 合并
  
  ci_config:
    jenkins: "internet-jenkins"
    auto_trigger: true
    trigger_branch: "develop"
    
  cd_config:
    integrated: true  # 与 CI 在同一流水线
    auto_deploy: true
    approval_required: false
    
  stages:
    - Checkout
    - Build
    - Test
    - DockerBuild
    - DockerPush
    - Deploy
```

#### 6.1.2 准生产环境策略

```yaml
strategy:
  name: "准生产环境分离策略"
  code: "staging-separated"
  environment: "staging"
  pipeline_mode: "separated"  # CI/CD 分离
  
  ci_config:
    jenkins: "internet-jenkins"
    auto_trigger: true
    trigger_branch: "release/*"
    artifact_storage: "harbor"
    
  cd_config:
    jenkins: "government-jenkins"  # 政务网 Jenkins
    network: "isolated"  # 网络隔离
    sync_method: "export"  # 配置导出
    auto_deploy: false
    approval_required: true
    
  stages_ci:
    - Checkout
    - Build
    - Test
    - DockerBuild
    - DockerPush
    
  stages_cd:
    - ImageSync  # 镜像同步
    - Deploy
    - HealthCheck
```

#### 6.1.3 生产环境策略

```yaml
strategy:
  name: "生产环境分离策略"
  code: "production-separated"
  environment: "production"
  pipeline_mode: "separated"
  
  ci_config:
    jenkins: "internet-jenkins"
    auto_trigger: false  # 手动触发
    trigger_branch: "main"
    
  cd_config:
    jenkins: "government-jenkins"
    network: "isolated"
    sync_method: "export"
    auto_deploy: false
    approval_required: true
    approvers: ["ops-admin", "security-admin"]
    
  compliance:
    change_request_required: true
    audit_logging: true
    rollback_enabled: true
```

### 6.2 CI/CD 分离流程

```
┌──────────────────────────────────────────────────────────────────┐
│                        CI 流程 (互联网 Jenkins)                    │
├──────────────────────────────────────────────────────────────────┤
│  1. 代码检出                                                      │
│  2. 构建                                                          │
│  3. 单元测试                                                      │
│  4. 代码质量扫描                                                  │
│  5. Docker 镜像构建                                               │
│  6. 镜像推送到 Harbor (互联网)                                    │
│  7. 生成 CD 配置文件                                              │
│     ├── Jenkinsfile.cd (CD 流水线)                               │
│     ├── deploy-config.json (部署配置)                            │
│     └── ansible-playbooks/ (Ansible 剧本)                        │
│  8. 保存配置到平台                                                │
└──────────────────────────────────────────────────────────────────┘
                              ↓
                    ════════════════════
                    配置导出 / 手动同步
                    ════════════════════
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│                        CD 流程 (政务网 Jenkins)                    │
├──────────────────────────────────────────────────────────────────┤
│  1. 导入 CD 配置                                                  │
│     ├── 创建 Jenkins Job (粘贴 Jenkinsfile.cd)                   │
│     └── 或通过 API 导入                                          │
│  2. 镜像同步 (从互联网 Harbor 到政务网 Harbor)                    │
│  3. Ansible 部署 Docker 容器                                     │
│     ├── 拉取镜像                                                  │
│     ├── 停止旧容器                                                │
│     ├── 启动新容器                                                │
│     └── 健康检查                                                  │
│  4. 通知                                                          │
└──────────────────────────────────────────────────────────────────┘
```

---

## 7. CD 配置导出设计

### 7.1 导出内容

#### 7.1.1 Jenkinsfile.cd

```groovy
// 自动生成的 CD 流水线
// 应用: myapp
// 环境: production
// 版本: v1.2.3
// 生成时间: 2026-03-01 16:00:00
// 部署方式: Ansible Docker

pipeline {
    agent {
        label 'ansible'  // 使用安装了 Ansible 的 Agent
    }

    environment {
        APP_NAME = 'myapp'
        ENVIRONMENT = 'production'
        IMAGE_TAG = 'harbor.gov.cn/myproject/myapp:v1.2.3'
        ANSIBLE_INVENTORY = 'inventory/production'
        PLAYBOOK_PATH = 'playbooks/deploy-docker.yml'
    }

    stages {
        stage('镜像同步确认') {
            steps {
                script {
                    // 确认镜像已同步到政务网 Harbor
                    sh '''
                        curl -s -u ${HARBOR_USER}:${HARBOR_PASS} \
                            https://harbor.gov.cn/api/v2.0/projects/myproject/repositories/myapp/artifacts | \
                            grep -q "${IMAGE_TAG}"
                    '''
                }
            }
        }

        stage('Ansible 部署前检查') {
            steps {
                sh '''
                    ansible --version
                    ansible all -i ${ANSIBLE_INVENTORY} -m ping
                '''
            }
        }

        stage('部署 Docker 容器') {
            steps {
                sh '''
                    ansible-playbook -i ${ANSIBLE_INVENTORY} ${PLAYBOOK_PATH} \
                        -e "app_name=${APP_NAME}" \
                        -e "environment=${ENVIRONMENT}" \
                        -e "image_tag=${IMAGE_TAG}" \
                        -e "docker_registry=${HARBOR_REGISTRY}" \
                        --tags "deploy" \
                        -v
                '''
            }
        }

        stage('健康检查') {
            steps {
                sh '''
                    ansible-playbook -i ${ANSIBLE_INVENTORY} ${PLAYBOOK_PATH} \
                        -e "app_name=${APP_NAME}" \
                        -e "environment=${ENVIRONMENT}" \
                        --tags "healthcheck" \
                        -v
                '''
            }
        }

        stage('部署验证') {
            steps {
                sh '''
                    ansible all -i ${ANSIBLE_INVENTORY} -m shell \
                        -a "docker ps --filter name=${APP_NAME} --format '{{.Status}}'"
                '''
            }
        }
    }

    post {
        success {
            echo '部署成功'
            // 发送成功通知
            sh '''
                ansible-playbook -i ${ANSIBLE_INVENTORY} playbooks/notify.yml \
                    -e "app_name=${APP_NAME}" \
                    -e "status=success" \
                    -e "version=${IMAGE_TAG}"
            '''
        }
        failure {
            echo '部署失败，执行回滚'
            // 自动回滚
            sh '''
                ansible-playbook -i ${ANSIBLE_INVENTORY} ${PLAYBOOK_PATH} \
                    -e "app_name=${APP_NAME}" \
                    -e "environment=${ENVIRONMENT}" \
                    --tags "rollback" \
                    -v || true
            '''
        }
    }
}
```

#### 7.1.2 deploy-config.json

```json
{
  "application": {
    "name": "myapp",
    "code": "myapp",
    "version": "v1.2.3",
    "language": "java",
    "framework": "springboot"
  },
  "environment": "production",
  "image": {
    "registry": "harbor.gov.cn",
    "project": "myproject",
    "name": "myapp",
    "tag": "v1.2.3",
    "digest": "sha256:abc123..."
  },
  "ansible": {
    "inventory": "inventory/production",
    "playbook": "playbooks/deploy-docker.yml",
    "extra_vars": {
      "app_name": "myapp",
      "container_port": 8080,
      "host_port": 8080,
      "replicas": 1,
      "memory_limit": "2g",
      "cpu_limit": "2"
    }
  },
  "docker": {
    "container_name": "myapp-production",
    "ports": ["8080:8080"],
    "volumes": ["/data/myapp/logs:/app/logs"],
    "environment": {
      "SPRING_PROFILES_ACTIVE": "production",
      "JAVA_OPTS": "-Xmx1536m -Xms512m"
    },
    "networks": ["app-network"],
    "restart_policy": "always",
    "healthcheck": {
      "test": ["CMD", "curl", "-f", "http://localhost:8080/actuator/health"],
      "interval": "30s",
      "timeout": "10s",
      "retries": 3
    }
  },
  "servers": [
    {
      "name": "app-server-01",
      "host": "192.168.1.101",
      "tags": ["app", "primary"]
    },
    {
      "name": "app-server-02",
      "host": "192.168.1.102",
      "tags": ["app", "secondary"]
    }
  ],
  "healthCheck": {
    "endpoint": "/actuator/health",
    "port": 8080,
    "timeout": 30,
    "retries": 3
  }
}
```

#### 7.1.3 Ansible Playbook 示例

**playbooks/deploy-docker.yml** - Docker 容器部署剧本：

```yaml
---
# Docker 容器部署 Playbook
# 应用: {{ app_name }}
# 环境: {{ environment }}
# 版本: {{ image_tag }}

- name: Deploy Docker Container
  hosts: all
  become: yes
  vars:
    app_name: "{{ app_name }}"
    environment: "{{ environment }}"
    image_tag: "{{ image_tag }}"
    docker_registry: "{{ docker_registry }}"
    container_port: "{{ container_port | default(8080) }}"
    host_port: "{{ host_port | default(8080) }}"
    memory_limit: "{{ memory_limit | default('1g') }}"
    cpu_limit: "{{ cpu_limit | default('1') }}"

  tasks:
    - name: 登录 Harbor 镜像仓库
      docker_login:
        registry: "{{ docker_registry }}"
        username: "{{ harbor_user }}"
        password: "{{ harbor_password }}"
      no_log: true

    - name: 拉取最新镜像
      docker_image:
        name: "{{ image_tag }}"
        source: pull
        force_source: yes

    - name: 停止旧容器
      docker_container:
        name: "{{ app_name }}-{{ environment }}"
        state: stopped
      ignore_errors: yes

    - name: 删除旧容器
      docker_container:
        name: "{{ app_name }}-{{ environment }}"
        state: absent
      ignore_errors: yes

    - name: 启动新容器
      docker_container:
        name: "{{ app_name }}-{{ environment }}"
        image: "{{ image_tag }}"
        state: started
        restart_policy: always
        ports:
          - "{{ host_port }}:{{ container_port }}"
        env:
          SPRING_PROFILES_ACTIVE: "{{ environment }}"
          JAVA_OPTS: "-Xmx{{ memory_limit | regex_replace('[^0-9]', '') | int // 2 }}m"
        memory: "{{ memory_limit }}"
        cpu_quota: "{{ (cpu_limit | int) * 100000 }}"
        healthcheck:
          test: ["CMD", "curl", "-f", "http://localhost:{{ container_port }}/actuator/health"]
          interval: 30s
          timeout: 10s
          retries: 3
          start_period: 60s
        networks:
          - name: app-network
      register: container_result

    - name: 等待容器健康
      command: >
        docker inspect --format='{{{{ .State.Health.Status }}}}'
        {{ app_name }}-{{ environment }}
      register: health_status
      until: health_status.stdout == 'healthy'
      retries: 10
      delay: 10
      tags: healthcheck

    - name: 部署成功通知
      debug:
        msg: "应用 {{ app_name }} 部署成功，容器状态: {{ health_status.stdout }}"
      tags: healthcheck

  handlers:
    - name: 回滚容器
      docker_container:
        name: "{{ app_name }}-{{ environment }}"
        state: started
        image: "{{ previous_image_tag | default(image_tag) }}"
      listen: rollback

  post_tasks:
    - name: 清理旧镜像
      docker_image_prune:
        images: yes
        images_filters:
          dangling: true
```

**inventory/production** - 主机清单示例：

```ini
[app_servers]
app-server-01 ansible_host=192.168.1.101
app-server-02 ansible_host=192.168.1.102

[app_servers:vars]
ansible_user=deploy
ansible_ssh_private_key_file=~/.ssh/id_rsa
ansible_python_interpreter=/usr/bin/python3

[all:vars]
harbor_registry=harbor.gov.cn
environment=production
```

**roles/docker-deploy/tasks/main.yml** - 部署任务模块：

```yaml
---
- name: 创建应用目录
  file:
    path: "/opt/apps/{{ app_name }}"
    state: directory
    mode: '0755'

- name: 复制配置文件
  template:
    src: "{{ item.src }}"
    dest: "/opt/apps/{{ app_name }}/{{ item.dest }}"
  loop:
    - { src: 'application.yml.j2', dest: 'application.yml' }
    - { src: 'logback.xml.j2', dest: 'logback.xml' }
  notify: restart container

- name: 创建 Docker 网络
  docker_network:
    name: app-network
    state: present
```

### 7.2 导出功能设计

#### 7.2.1 API 接口

```python
# 导出 CD 配置
POST /api/admin/release/applications/{id}/cd/export/

Request:
{
    "environment": "production",
    "format": "zip",  # jenkinsfile, json, yaml, zip
    "include_history": true
}

Response:
{
    "success": true,
    "data": {
        "export_id": 123,
        "download_url": "/api/admin/release/cd-exports/123/download/",
        "files": [
            "Jenkinsfile.cd",
            "deploy-config.json",
            "ansible/playbooks/deploy-docker.yml",
            "ansible/inventory/production",
            "ansible/roles/docker-deploy/tasks/main.yml",
            "ansible/roles/docker-deploy/templates/docker-compose.yml.j2"
        ],
        "expires_at": "2026-03-02T16:00:00Z"
    }
}
```

#### 7.2.2 前端界面

```
┌─────────────────────────────────────────────────────────────────┐
│  应用详情 > CD 配置 > 导出                                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  目标环境:  [生产环境 ▼]                                         │
│                                                                 │
│  配置版本:  [最新版本 ▼]  v1.2.3 (2026-03-01 16:00)             │
│                                                                 │
│  导出格式:  ○ Jenkinsfile    ○ JSON 配置                        │
│            ○ YAML 配置      ● 完整压缩包                        │
│                                                                 │
│  包含内容:  ☑ Jenkinsfile CD 流水线                              │
│            ☑ 部署配置 JSON                                       │
│            ☑ Ansible Playbook 部署剧本                           │
│            ☑ Ansible Inventory 主机清单                          │
│            ☑ 部署说明文档                                        │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Jenkinsfile 预览                                        │   │
│  │  ─────────────────────────────────────────────────────  │   │
│  │  pipeline {                                             │   │
│  │      agent { kubernetes { ... } }                       │   │
│  │      stages { ... }                                     │   │
│  │  }                                                      │   │
│  │                                                         │   │
│  │  [复制到剪贴板]                                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│                    [下载配置包]  [复制 Jenkinsfile]              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 7.3 政务网 Jenkins 导入

#### 7.3.1 手动导入流程

1. 下载配置包
2. 通过安全通道传输到政务网环境
3. 部署 Ansible 配置：
   - 将 `ansible/` 目录复制到 Ansible 控制节点
   - 根据实际情况修改 `inventory/production` 主机清单
   - 配置 SSH 免密登录到目标服务器
4. 配置 Jenkins：
   - 登录政务网 Jenkins
   - 创建新的 Pipeline Job
   - 将 `Jenkinsfile.cd` 内容粘贴到 Pipeline Script
   - 配置必要的凭据（Harbor 用户密码、SSH 密钥）
5. 执行部署

#### 7.3.2 API 导入（政务网 Jenkins 安装插件）

```groovy
// 政务网 Jenkins 插件配置
// 从 DevOps 平台拉取 CD 配置

import groovy.json.JsonSlurper

def loadCDConfig(String exportId, String token) {
    def url = "https://devops.gov.cn/api/admin/release/cd-exports/${exportId}/download/"
    def connection = new URL(url).openConnection()
    connection.setRequestProperty("Authorization", "Bearer ${token}")
    
    def response = connection.getInputStream().getText()
    def config = new JsonSlurper().parseText(response)
    
    return config
}

// 使用示例
node('ansible') {
    def cdConfig = loadCDConfig(params.EXPORT_ID, env.DEVOPS_TOKEN)
    
    stage('Deploy with Ansible') {
        sh """
            ansible-playbook -i inventory/${cdConfig.environment} \
                playbooks/deploy-docker.yml \
                -e "app_name=${cdConfig.application.name}" \
                -e "image_tag=${cdConfig.image.registry}/${cdConfig.image.project}/${cdConfig.image.name}:${cdConfig.image.tag}" \
                -e "environment=${cdConfig.environment}"
        """
    }
    
    stage('Health Check') {
        sh """
            ansible all -i inventory/${cdConfig.environment} \
                -m uri -a "url=http://localhost:${cdConfig.healthCheck.port}${cdConfig.healthCheck.endpoint} method=GET"
        """
    }
}
```

---

## 8. 版本管理设计

### 8.1 模板版本管理

```
模板版本生命周期:

v1.0.0 ──→ v1.0.1 ──→ v1.1.0 ──→ v2.0.0
  │          │          │          │
  │          │          │          └── 重大变更
  │          │          └── 功能增强
  │          └── Bug 修复
  └── 初始版本

版本规则:
- 主版本号: 重大变更，不兼容旧版本
- 次版本号: 功能增强，向后兼容
- 修订号: Bug 修复，向后兼容
```

#### 8.1.1 模板版本 API

```python
# 创建模板新版本
POST /api/admin/release/pipeline-templates/{id}/versions/

Request:
{
    "version": "1.1.0",
    "content": "...",
    "variables": {...},
    "stages": [...],
    "change_log": "新增代码质量扫描阶段",
    "copy_from": "1.0.0"  # 可选，从哪个版本复制
}

# 获取模板版本列表
GET /api/admin/release/pipeline-templates/{id}/versions/

# 设置最新版本
PUT /api/admin/release/pipeline-templates/{id}/versions/{version_id}/set-latest/
```

### 8.2 应用配置版本管理

```
应用配置版本历史:

v1 ──→ v2 ──→ v3 ──→ v4 (当前)
│      │      │      │
│      │      │      └── 更新生产环境配置
│      │      └── 新增测试环境配置
│      └── 切换到新模板版本
└── 初始配置

每次配置变更自动创建新版本
支持回滚到任意历史版本
```

#### 7.2.1 配置版本 API

```python
# 更新应用配置（自动创建新版本）
PUT /api/admin/release/application-pipeline-configs/{id}/

Request:
{
    "template_version_id": 123,
    "variables": {...},
    "stages_config": [...]
}

# 获取配置历史
GET /api/admin/release/application-pipeline-configs/{id}/versions/

# 回滚到历史版本
POST /api/admin/release/application-pipeline-configs/{id}/rollback/

Request:
{
    "target_version": 2
}
```

---

## 9. 功能模块设计

### 9.1 模板管理模块

#### 9.1.1 模板列表

```
┌─────────────────────────────────────────────────────────────────┐
│  CI/CD 模板管理                                                  │
├─────────────────────────────────────────────────────────────────┤
│  类型: [全部 ▼]  语言: [全部 ▼]  搜索: [________________] [查询] │
│                                                                 │
│  [+ 创建模板]                                                    │
│                                                                 │
│  ┌─────┬──────────────────┬────────┬────────┬─────────┬─────┐ │
│  │ 类型 │ 模板名称          │ 语言   │ 框架   │ 当前版本 │ 操作 │ │
│  ├─────┼──────────────────┼────────┼────────┼─────────┼─────┤ │
│  │ CI  │ Java SpringBoot  │ Java   │ Spring │ v2.1.0  │ 详情 │ │
│  │     │ Maven 构建       │        │ Boot   │         │ 编辑 │ │
│  │     │                  │        │        │         │ 版本 │ │
│  ├─────┼──────────────────┼────────┼────────┼─────────┼─────┤ │
│  │ CI  │ Vue 前端构建     │ Node.js│ Vue    │ v1.3.0  │ ...  │ │
│  ├─────┼──────────────────┼────────┼────────┼─────────┼─────┤ │
│  │ CD  │ Kubernetes 部署  │ -      │ K8s    │ v1.0.2  │ ...  │ │
│  └─────┴──────────────────┴────────┴────────┴─────────┴─────┘ │
└─────────────────────────────────────────────────────────────────┘
```

#### 9.1.2 模板编辑

```
┌─────────────────────────────────────────────────────────────────┐
│  编辑模板: Java SpringBoot Maven 构建                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  基本信息                                                        │
│  ───────────────────────────────────────────────────────────    │
│  模板名称: [Java SpringBoot Maven 构建        ]                 │
│  模板编码: ci-java-springboot-maven (不可修改)                   │
│  模板类型: ○ CI  ○ CD                                           │
│  编程语言: [Java        ▼]                                       │
│  语言版本: [17         ▼] (可选)                                 │
│  框架:     [Spring Boot ▼] (可选)                                │
│  描述:     [________________________________]                    │
│                                                                 │
│  模板内容                                                        │
│  ───────────────────────────────────────────────────────────    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  1  pipeline {                                          │   │
│  │  2      agent {                                         │   │
│  │  3          kubernetes {                                │   │
│  │  4              yaml '''                                │   │
│  │  5  ...                                                 │   │
│  │  │                                                      │   │
│  │  [语法高亮] [变量插入] [阶段配置]                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  变量定义                                                        │
│  ───────────────────────────────────────────────────────────    │
│  [+ 添加变量]                                                    │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐      │
│  │ 变量名    │ 类型      │ 标签     │ 默认值   │ 操作     │      │
│  ├──────────┼──────────┼──────────┼──────────┼──────────┤      │
│  │ JAVA_VER │ select   │ Java版本 │ 17       │ 编辑 删除 │      │
│  │ MAVEN_OPT│ string   │ Maven参数│ -Xmx1g   │ 编辑 删除 │      │
│  └──────────┴──────────┴──────────┴──────────┴──────────┘      │
│                                                                 │
│  阶段配置                                                        │
│  ───────────────────────────────────────────────────────────    │
│  [拖拽排序]                                                      │
│  ┌──────┬──────┬──────┬──────┬──────┬──────┐                   │
│  │ 检出 │ 构建 │ 测试 │ 质量 │ 打包 │ 推送 │                   │
│  └──────┴──────┴──────┴──────┴──────┴──────┘                   │
│                                                                 │
│                              [保存] [保存为新版本] [预览]         │
└─────────────────────────────────────────────────────────────────┘
```

### 9.2 应用配置模块

#### 9.2.1 应用 CI/CD 配置

```
┌─────────────────────────────────────────────────────────────────┐
│  应用: myapp > CI/CD 配置                                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  环境       │ CI 配置          │ CD 配置          │ 操作   │ │
│  ├───────────────────────────────────────────────────────────┤ │
│  │  开发环境   │ ✅ 已配置 v2.1   │ ✅ 已配置 v1.0   │ 编辑   │ │
│  │  测试环境   │ ✅ 已配置 v2.1   │ ✅ 已配置 (集成) │ 编辑   │ │
│  │  准生产环境 │ ✅ 已配置 v2.0   │ ⏳ 待导出        │ 编辑   │ │
│  │  生产环境   │ ✅ 已配置 v1.8   │ ⏳ 待导出        │ 编辑   │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  配置版本历史                                                    │
│  ───────────────────────────────────────────────────────────    │
│  ┌──────┬──────────┬──────────────┬──────────┬──────────┐      │
│  │ 版本 │ 环境     │ 变更内容      │ 操作人   │ 操作     │      │
│  ├──────┼──────────┼──────────────┼──────────┼──────────┤      │
│  │ v4   │ 生产     │ 更新镜像标签  │ admin    │ 回滚 查看│      │
│  │ v3   │ 测试     │ 启用集成模式  │ admin    │ 回滚 查看│      │
│  │ v2   │ 准生产   │ 切换模板版本  │ admin    │ 回滚 查看│      │
│  │ v1   │ -        │ 初始配置      │ admin    │ 查看     │      │
│  └──────┴──────────┴──────────────┴──────────┴──────────┘      │
└─────────────────────────────────────────────────────────────────┘
```

#### 9.2.2 环境配置详情

```
┌─────────────────────────────────────────────────────────────────┐
│  配置: myapp - 生产环境                                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [CI 配置] [CD 配置]                                             │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  CI 配置                                                 │   │
│  │  ─────────────────────────────────────────────────────  │   │
│  │  模板: Java SpringBoot Maven 构建 (v2.1.0)              │   │
│  │  流水线模式: 分离模式 (CI/CD 分离)                        │   │
│  │  目标 Jenkins: internet-jenkins                         │   │
│  │                                                         │   │
│  │  变量配置:                                               │   │
│  │  ┌──────────────┬──────────────┐                        │   │
│  │  │ Java 版本    │ 17           │                        │   │
│  │  │ Maven 参数   │ -Xmx2g       │                        │   │
│  │  │ 跳过测试     │ 否           │                        │   │
│  │  │ Sonar 启用   │ 是           │                        │   │
│  │  └──────────────┴──────────────┘                        │   │
│  │                                                         │   │
│  │  阶段配置:                                               │   │
│  │  ☑ 代码检出  ☑ 构建  ☑ 测试  ☑ 代码质量  ☑ 镜像构建     │   │
│  │                                                         │   │
│  │  [生成 Jenkinsfile] [应用到 Jenkins]                     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  CD 配置                                                 │   │
│  │  ─────────────────────────────────────────────────────  │   │
│  │  模板: Kubernetes 容器部署 (v1.0.2)                      │   │
│  │  流水线模式: 分离模式                                    │   │
│  │  目标 Jenkins: government-jenkins (政务网)               │   │
│  │                                                         │   │
│  │  部署配置:                                               │   │
│  │  ┌──────────────┬──────────────┐                        │   │
│  │  │ 命名空间     │ production   │                        │   │
│  │  │ 副本数       │ 3            │                        │   │
│  │  │ 资源限制     │ 2核/2Gi      │                        │   │
│  │  │ 健康检查     │ /health      │                        │   │
│  │  └──────────────┴──────────────┘                        │   │
│  │                                                         │   │
│  │  审批配置:                                               │   │
│  │  ☑ 需要审批  审批人: ops-admin, security-admin          │   │
│  │                                                         │   │
│  │  [导出配置] [查看导出历史]                               │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│                              [保存配置] [立即执行 CI]            │
└─────────────────────────────────────────────────────────────────┘
```

### 9.3 配置导出模块

#### 9.3.1 导出界面

```
┌─────────────────────────────────────────────────────────────────┐
│  导出 CD 配置                                                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  应用: myapp                                                    │
│  环境: 生产环境                                                  │
│  配置版本: v4 (最新)                                             │
│                                                                 │
│  导出格式:                                                       │
│  ○ Jenkinsfile - 仅 CD 流水线脚本                                │
│  ○ JSON - 部署配置文件                                           │
│  ○ YAML - Kubernetes 清单                                       │
│  ● 完整包 - 包含所有配置文件                                      │
│                                                                 │
│  导出内容预览:                                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  📁 myapp-cd-production-v4/                             │   │
│  │     ├── 📄 Jenkinsfile.cd          (CD 流水线)          │   │
│  │     ├── 📄 deploy-config.json      (部署配置)           │   │
│  │     ├── 📄 README.md               (部署说明)           │   │
│  │     └── 📁 ansible/                                      │   │
│  │         ├── 📁 playbooks/                                │   │
│  │         │   ├── deploy-docker.yml  (部署剧本)           │   │
│  │         │   └── notify.yml         (通知剧本)           │   │
│  │         ├── 📁 inventory/                                │   │
│  │         │   └── production         (主机清单)           │   │
│  │         └── 📁 roles/                                   │   │
│  │             └── 📁 docker-deploy/                        │   │
│  │                 ├── tasks/main.yml  (部署任务)           │   │
│  │                 └── templates/     (配置模板)           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  使用说明:                                                       │
│  1. 下载配置包                                                   │
│  2. 通过安全通道传输到政务网                                      │
│  3. 在政务网 Jenkins 中创建 Pipeline Job                         │
│  4. 将 Jenkinsfile.cd 内容粘贴到 Pipeline Script                 │
│  5. 将 ansible 目录放到 Ansible 工作目录                         │
│  6. 配置必要的凭据 (Harbor、目标服务器)                           │
│  7. 执行部署                                                     │
│                                                                 │
│         [下载配置包]  [复制 Jenkinsfile]  [复制配置 JSON]         │
└─────────────────────────────────────────────────────────────────┘
```

#### 9.3.2 导出历史

```
┌─────────────────────────────────────────────────────────────────┐
│  CD 配置导出历史                                                 │
├─────────────────────────────────────────────────────────────────┤
│  应用: myapp    环境: 生产环境                                    │
│                                                                 │
│  ┌──────┬────────────┬──────────┬──────────┬──────────┐        │
│  │ 版本 │ 导出时间    │ 导出人   │ 下载次数 │ 操作     │        │
│  ├──────┼────────────┼──────────┼──────────┼──────────┤        │
│  │ v4   │ 2026-03-01 │ admin    │ 3        │ 下载 查看│        │
│  │ v3   │ 2026-02-28 │ admin    │ 5        │ 下载 查看│        │
│  │ v2   │ 2026-02-27 │ ops      │ 2        │ 下载 查看│        │
│  │ v1   │ 2026-02-25 │ admin    │ 1        │ 下载 查看│        │
│  └──────┴────────────┴──────────┴──────────┴──────────┘        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 10. 接口设计

### 10.1 模板管理接口

```python
# 模板列表
GET /api/admin/release/pipeline-templates/
    ?template_type=ci
    &language=java
    &search=keyword

# 创建模板
POST /api/admin/release/pipeline-templates/
{
    "name": "Java SpringBoot Maven 构建",
    "code": "ci-java-springboot-maven",
    "template_type": "ci",
    "language": "java",
    "framework": "springboot",
    "description": "..."
}

# 模板详情
GET /api/admin/release/pipeline-templates/{id}/

# 更新模板
PUT /api/admin/release/pipeline-templates/{id}/

# 删除模板
DELETE /api/admin/release/pipeline-templates/{id}/

# 模板版本列表
GET /api/admin/release/pipeline-templates/{id}/versions/

# 创建模板版本
POST /api/admin/release/pipeline-templates/{id}/versions/
{
    "version": "1.1.0",
    "content": "...",
    "variables": {...},
    "stages": [...],
    "change_log": "..."
}

# 设置最新版本
PUT /api/admin/release/pipeline-templates/{id}/versions/{version_id}/set-latest/

# 预览生成的 Jenkinsfile
POST /api/admin/release/pipeline-templates/{id}/preview/
{
    "variables": {...},
    "stages_config": [...]
}
```

### 10.2 应用配置接口

```python
# 应用 CI/CD 配置列表
GET /api/admin/release/applications/{id}/pipeline-configs/

# 创建/更新应用配置
POST /api/admin/release/applications/{id}/pipeline-configs/
{
    "config_type": "ci",
    "environment": "production",
    "template_id": 1,
    "template_version_id": 5,
    "variables": {...},
    "stages_config": [...]
}

# 配置详情
GET /api/admin/release/application-pipeline-configs/{id}/

# 配置版本历史
GET /api/admin/release/application-pipeline-configs/{id}/versions/

# 回滚配置
POST /api/admin/release/application-pipeline-configs/{id}/rollback/
{
    "target_version": 2
}

# 生成 Jenkinsfile
POST /api/admin/release/application-pipeline-configs/{id}/generate/

# 应用到 Jenkins
POST /api/admin/release/application-pipeline-configs/{id}/apply/
```

### 10.3 CD 导出接口

```python
# 导出 CD 配置
POST /api/admin/release/applications/{id}/cd/export/
{
    "environment": "production",
    "format": "zip",
    "version": null  # null 表示最新版本
}

# 导出记录列表
GET /api/admin/release/cd-exports/
    ?application_id=1
    &environment=production

# 下载导出文件
GET /api/admin/release/cd-exports/{id}/download/

# 导出详情
GET /api/admin/release/cd-exports/{id}/

# 复制 Jenkinsfile (返回纯文本)
GET /api/admin/release/cd-exports/{id}/jenkinsfile/

# 复制配置 JSON
GET /api/admin/release/cd-exports/{id}/json/
```

### 10.4 环境策略接口

```python
# 策略列表
GET /api/admin/release/environment-strategies/

# 创建策略
POST /api/admin/release/environment-strategies/
{
    "name": "生产环境分离策略",
    "code": "production-separated",
    "environment": "production",
    "pipeline_mode": "separated",
    "ci_jenkins": "internet-jenkins",
    "cd_jenkins": "government-jenkins",
    "requires_approval": true,
    ...
}

# 策略详情
GET /api/admin/release/environment-strategies/{id}/

# 更新策略
PUT /api/admin/release/environment-strategies/{id}/
```

---

## 11. 数据库迁移计划

### 11.1 新增表

```sql
-- 流水线模板表
CREATE TABLE release_pipeline_template (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(128) NOT NULL,
    code VARCHAR(64) NOT NULL UNIQUE,
    template_type VARCHAR(20) NOT NULL,
    language VARCHAR(32) NOT NULL,
    language_version VARCHAR(32),
    framework VARCHAR(64),
    description TEXT,
    is_official BOOLEAN DEFAULT FALSE,
    status BOOLEAN DEFAULT TRUE,
    -- CoreModel 字段
    remark VARCHAR(256),
    creator VARCHAR(64),
    modifier VARCHAR(64),
    update_time DATETIME,
    create_time DATETIME,
    is_deleted BOOLEAN DEFAULT FALSE
);

-- 模板版本表
CREATE TABLE release_pipeline_template_version (
    id INT PRIMARY KEY AUTO_INCREMENT,
    template_id INT NOT NULL,
    version VARCHAR(32) NOT NULL,
    content TEXT NOT NULL,
    variables JSON,
    stages JSON,
    change_log TEXT,
    is_latest BOOLEAN DEFAULT FALSE,
    status BOOLEAN DEFAULT TRUE,
    -- CoreModel 字段
    remark VARCHAR(256),
    creator VARCHAR(64),
    modifier VARCHAR(64),
    update_time DATETIME,
    create_time DATETIME,
    is_deleted BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (template_id) REFERENCES release_pipeline_template(id),
    UNIQUE KEY (template_id, version)
);

-- 应用流水线配置表
CREATE TABLE release_application_pipeline_config (
    id INT PRIMARY KEY AUTO_INCREMENT,
    application_id INT NOT NULL,
    config_type VARCHAR(20) NOT NULL,
    environment VARCHAR(32) NOT NULL,
    template_id INT,
    template_version_id INT,
    custom_content TEXT,
    variables JSON,
    stages_config JSON,
    is_active BOOLEAN DEFAULT TRUE,
    -- CoreModel 字段
    remark VARCHAR(256),
    creator VARCHAR(64),
    modifier VARCHAR(64),
    update_time DATETIME,
    create_time DATETIME,
    is_deleted BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (application_id) REFERENCES release_application(id),
    FOREIGN KEY (template_id) REFERENCES release_pipeline_template(id),
    FOREIGN KEY (template_version_id) REFERENCES release_pipeline_template_version(id),
    UNIQUE KEY (application_id, config_type, environment)
);

-- 应用配置版本表
CREATE TABLE release_application_pipeline_version (
    id INT PRIMARY KEY AUTO_INCREMENT,
    config_id INT NOT NULL,
    version INT NOT NULL,
    content TEXT NOT NULL,
    variables_snapshot JSON,
    stages_snapshot JSON,
    generated_at DATETIME,
    generated_by VARCHAR(64),
    -- CoreModel 字段
    remark VARCHAR(256),
    creator VARCHAR(64),
    modifier VARCHAR(64),
    update_time DATETIME,
    create_time DATETIME,
    is_deleted BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (config_id) REFERENCES release_application_pipeline_config(id),
    UNIQUE KEY (config_id, version)
);

-- 环境策略表
CREATE TABLE release_environment_strategy (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(64) NOT NULL,
    code VARCHAR(32) NOT NULL UNIQUE,
    environment VARCHAR(32) NOT NULL,
    pipeline_mode VARCHAR(32) NOT NULL,
    ci_jenkins VARCHAR(128),
    cd_jenkins VARCHAR(128),
    requires_approval BOOLEAN DEFAULT FALSE,
    auto_deploy BOOLEAN DEFAULT FALSE,
    description TEXT,
    is_default BOOLEAN DEFAULT FALSE,
    -- CoreModel 字段
    remark VARCHAR(256),
    creator VARCHAR(64),
    modifier VARCHAR(64),
    update_time DATETIME,
    create_time DATETIME,
    is_deleted BOOLEAN DEFAULT FALSE
);

-- CD 配置导出表
CREATE TABLE release_cd_config_export (
    id INT PRIMARY KEY AUTO_INCREMENT,
    application_id INT NOT NULL,
    environment VARCHAR(32) NOT NULL,
    version INT NOT NULL,
    export_format VARCHAR(20) NOT NULL,
    content LONGTEXT,
    file_path VARCHAR(512),
    exported_by VARCHAR(64),
    download_count INT DEFAULT 0,
    -- CoreModel 字段
    remark VARCHAR(256),
    creator VARCHAR(64),
    modifier VARCHAR(64),
    update_time DATETIME,
    create_time DATETIME,
    is_deleted BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (application_id) REFERENCES release_application(id)
);
```

### 11.2 应用表扩展

```sql
-- 扩展应用表
ALTER TABLE release_application ADD COLUMN current_ci_version INT;
ALTER TABLE release_application ADD COLUMN current_cd_version INT;
ALTER TABLE release_application ADD COLUMN last_ci_build_time DATETIME;
ALTER TABLE release_application ADD COLUMN last_cd_deploy_time DATETIME;
```

---

## 12. 开发计划

### 12.1 阶段一：模板系统（预计 2 周）

| 任务 | 工作量 | 优先级 |
|------|--------|--------|
| 数据模型设计与迁移 | 2天 | P0 |
| 模板管理后端 API | 3天 | P0 |
| 模板版本管理 | 2天 | P0 |
| 模板管理前端页面 | 3天 | P0 |
| 内置模板导入 | 2天 | P1 |

### 12.2 阶段二：应用配置（预计 2 周）

| 任务 | 工作量 | 优先级 |
|------|--------|--------|
| 应用配置模型与 API | 3天 | P0 |
| Jenkinsfile 生成引擎 | 3天 | P0 |
| 配置版本管理 | 2天 | P0 |
| 应用配置前端页面 | 3天 | P0 |
| Jenkins 自动应用 | 2天 | P1 |

### 12.3 阶段三：环境策略（预计 1 周）

| 任务 | 工作量 | 优先级 |
|------|--------|--------|
| 环境策略模型与 API | 2天 | P0 |
| 策略配置前端页面 | 2天 | P0 |
| 测试环境集成模式 | 1天 | P0 |
| 准生产/生产分离模式 | 2天 | P1 |

### 12.4 阶段四：CD 导出（预计 1 周）

| 任务 | 工作量 | 优先级 |
|------|--------|--------|
| CD 配置导出模型与 API | 2天 | P0 |
| 导出文件生成引擎 | 2天 | P0 |
| 导出管理前端页面 | 2天 | P0 |
| 导出历史与下载 | 1天 | P1 |

---

## 13. 风险与应对

### 13.1 技术风险

| 风险 | 影响 | 应对措施 |
|------|------|----------|
| 模板语法复杂度高 | 用户学习成本增加 | 提供可视化编辑器、丰富示例 |
| 跨网络同步延迟 | 部署时效性降低 | 支持离线包、自动化同步脚本 |
| 版本兼容性问题 | 升级困难 | 严格的版本管理、向后兼容策略 |

### 13.2 业务风险

| 风险 | 影响 | 应对措施 |
|------|------|----------|
| 配置导出安全风险 | 敏感信息泄露 | 敏感变量加密、脱敏导出 |
| 审批流程缺失 | 生产事故 | 强制审批、操作审计 |
| 模板维护成本 | 模板过时 | 定期更新、社区贡献机制 |

---

## 14. 附录

### 14.1 内置模板清单

#### CI 模板

1. **ci-java-springboot-maven** - Java SpringBoot Maven 构建
2. **ci-java-springboot-gradle** - Java SpringBoot Gradle 构建
3. **ci-java-springcloud-maven** - Java SpringCloud Maven 构建
4. **ci-python-django** - Python Django 构建
5. **ci-python-flask** - Python Flask 构建
6. **ci-python-fastapi** - Python FastAPI 构建
7. **ci-nodejs-vue** - Node.js Vue 构建
8. **ci-nodejs-react** - Node.js React 构建
9. **ci-nodejs-nextjs** - Node.js Next.js 构建
10. **ci-go-gin** - Go Gin 构建
11. **ci-go-beego** - Go Beego 构建
12. **ci-dotnet-aspnet** - .NET Core ASP.NET 构建

#### CD 模板（Ansible 部署）

1. **cd-ansible-docker** - Ansible Docker 单机部署
2. **cd-ansible-compose** - Ansible Docker Compose 编排部署
3. **cd-ansible-swarm** - Ansible Docker Swarm 集群部署
4. **cd-ansible-k8s** - Ansible Kubernetes 部署（通过 kubectl）
5. **cd-ansible-script** - Ansible 传统脚本部署

### 14.2 变量命名规范

| 前缀 | 含义 | 示例 |
|------|------|------|
| `BUILD_` | 构建相关 | `BUILD_TOOL`, `BUILD_ARGS` |
| `DEPLOY_` | 部署相关 | `DEPLOY_TARGET`, `DEPLOY_REPLICAS` |
| `DOCKER_` | Docker 相关 | `DOCKER_REGISTRY`, `DOCKER_TAG` |
| `ANSIBLE_` | Ansible 相关 | `ANSIBLE_INVENTORY`, `ANSIBLE_PLAYBOOK` |
| `APP_` | 应用相关 | `APP_NAME`, `APP_PORT` |
| `CONTAINER_` | 容器相关 | `CONTAINER_NAME`, `CONTAINER_PORT` | |

### 14.3 参考资料

- Jenkins Pipeline 语法: https://www.jenkins.io/doc/book/pipeline/syntax/
- Kubernetes 部署最佳实践: https://kubernetes.io/docs/concepts/workloads/controllers/deployment/
- GitLab CI/CD 配置: https://docs.gitlab.com/ee/ci/yaml/

---

## 修订历史

| 版本 | 日期 | 作者 | 变更内容 |
|------|------|------|----------|
| v1.0 | 2026-03-01 | DevOps Team | 初始版本 |
