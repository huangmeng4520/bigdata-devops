# Jenkins Pipeline 模版管理系统 PRD

## 1. 项目概述

### 1.1 背景
为了标准化和简化 CI/CD 流水线的创建和管理，需要构建一个完善的 Jenkins Pipeline 模版管理系统，支持不同语言、不同场景的流水线模版，并实现模版的版本管理、复制、导入导出等功能。

### 1.2 目标
- 提供标准化的流水线模版，覆盖主流编程语言和框架
- 支持模版的版本管理和自动迭代
- 实现模版与应用的关联和同步
- 支持模版的复制、导入、导出，便于跨环境迁移
- 支持 Pipeline 各阶段脚本的独立编辑和管理

## 2. 功能需求

### 2.1 模版管理

#### 2.1.1 模版基本信息
- **模版名称**: 模版的显示名称
- **模版编码**: 唯一标识，用于系统内部引用
- **模版类型**: CI 模版 / CD 模版
- **编程语言**: Java、Python、Node.js、Go、.NET 等
- **语言版本**: 如 Java 8、Python 3.9 等
- **框架**: Spring Boot、Django、Express 等
- **描述**: 模版的详细说明
- **官方模版**: 标识是否为官方提供的标准模版
- **状态**: 启用/禁用

#### 2.1.2 模版操作
- **创建模版**: 创建新的流水线模版，同时创建初始版本
- **编辑模版**: 修改模版基本信息（不包括版本内容）
- **复制模版**: 基于现有模版创建副本，自动复制最新版本
- **删除模版**: 软删除模版及其所有版本
- **导出模版**: 导出模版配置为 JSON 文件
- **导入模版**: 从 JSON 文件导入模版配置

### 2.2 版本管理

#### 2.2.1 版本信息
- **版本号**: 遵循语义化版本规范（如 1.0.0）
- **模版内容**: Jenkinsfile 脚本内容
- **变量定义**: 模版中使用的变量及其默认值
- **阶段定义**: Pipeline 的各个阶段配置
- **阶段脚本**: 各阶段的独立脚本内容（stages_content）
- **变更日志**: 版本变更说明
- **是否最新**: 标识当前版本是否为最新版本
- **状态**: 启用/禁用

#### 2.2.2 版本操作
- **创建版本**: 手动创建新版本
- **自动版本迭代**: 基于现有版本自动创建新版本，版本号自动递增（如 1.0.0 → 1.0.1）
- **设为最新**: 将指定版本设置为最新版本
- **查看内容**: 查看版本的完整 Jenkinsfile 内容
- **编辑阶段**: 独立编辑某个阶段的脚本内容
- **版本预览**: 预览变量替换后的最终 Jenkinsfile

### 2.3 阶段管理

#### 2.3.1 阶段定义
Pipeline 通常包含以下标准阶段：
- **Checkout**: 代码检出
- **Build**: 编译构建
- **Test**: 单元测试
- **Code Analysis**: 代码质量分析
- **Build Image**: 构建 Docker 镜像
- **Push Image**: 推送镜像到仓库
- **Deploy**: 部署应用
- **Health Check**: 健康检查

#### 2.3.2 阶段脚本编辑
- 支持针对单个阶段独立编辑脚本
- 阶段脚本存储在 `stages_content` 字段中
- 修改阶段脚本时自动更新版本的 `update_time` 和 `modifier`

### 2.4 模版与应用关联

#### 2.4.1 应用配置
- 应用创建时可选择关联的流水线模版
- 选择模版后自动获取最新版本的配置
- 应用可以指定使用模版的特定版本

#### 2.4.2 模版同步
- 应用可以切换关联的模版
- 切换模版后自动同步到 Jenkins
- 支持查看模版变更历史

### 2.5 导入导出

#### 2.5.1 导出格式
```json
{
  "template": {
    "name": "Java Maven CI 模版",
    "code": "java_maven_ci",
    "template_type": "ci",
    "language": "java",
    "language_version": "11",
    "framework": "Spring Boot",
    "description": "Java Maven 项目的标准 CI 流水线"
  },
  "version": {
    "version": "1.0.0",
    "content": "pipeline { ... }",
    "variables": {
      "MAVEN_OPTS": "-Dmaven.repo.local=/root/.m2/repository"
    },
    "stages": [
      {"name": "Checkout", "description": "代码检出"},
      {"name": "Build", "description": "Maven 构建"}
    ],
    "stages_content": {
      "Checkout": "checkout scm",
      "Build": "sh 'mvn clean package -DskipTests'"
    }
  }
}
```

#### 2.5.2 导入规则
- 检查模版编码是否已存在，存在则报错
- 自动创建模版和初始版本
- 导入的模版默认为非官方模版
- 导入的版本自动设为最新版本

## 3. 技术实现

### 3.1 数据模型

#### 3.1.1 PipelineTemplate（流水线模版）
```python
class PipelineTemplate(CoreModel):
    name = CharField(max_length=128)  # 模版名称
    code = CharField(max_length=64, unique=True)  # 模版编码
    template_type = CharField(choices=['ci', 'cd'])  # 模版类型
    language = CharField(max_length=32)  # 编程语言
    language_version = CharField(max_length=32, blank=True)  # 语言版本
    framework = CharField(max_length=64, blank=True)  # 框架
    description = TextField(blank=True)  # 描述
    is_official = BooleanField(default=False)  # 官方模版
    status = IntegerField(default=1)  # 状态
```

#### 3.1.2 PipelineTemplateVersion（模版版本）
```python
class PipelineTemplateVersion(CoreModel):
    template = ForeignKey(PipelineTemplate)  # 所属模版
    version = CharField(max_length=32)  # 版本号
    content = TextField()  # 模版内容
    variables = JSONField(default=dict)  # 变量定义
    stages = JSONField(default=list)  # 阶段定义
    stages_content = JSONField(default=dict)  # 阶段脚本内容（新增）
    change_log = TextField(blank=True)  # 变更日志
    is_latest = BooleanField(default=False)  # 是否最新
    status = IntegerField(default=1)  # 状态
    
    def auto_increment_version(self):
        """自动递增版本号"""
        # 1.0.0 → 1.0.1
```

### 3.2 API 接口

#### 3.2.1 模版管理接口
- `GET /api/release/pipeline-templates/` - 获取模版列表
- `POST /api/release/pipeline-templates/` - 创建模版
- `GET /api/release/pipeline-templates/{id}/` - 获取模版详情
- `PUT /api/release/pipeline-templates/{id}/` - 更新模版
- `DELETE /api/release/pipeline-templates/{id}/` - 删除模版
- `POST /api/release/pipeline-templates/{id}/copy/` - 复制模版
- `GET /api/release/pipeline-templates/{id}/export_config/` - 导出模版
- `POST /api/release/pipeline-templates/import_config/` - 导入模版

#### 3.2.2 版本管理接口
- `GET /api/release/pipeline-templates/{id}/versions/` - 获取版本列表
- `POST /api/release/pipeline-templates/{id}/create_version/` - 创建版本
- `POST /api/release/pipeline-template-versions/{id}/set_latest/` - 设为最新
- `POST /api/release/pipeline-template-versions/{id}/auto_version/` - 自动版本迭代
- `PUT /api/release/pipeline-template-versions/{id}/update_stage/` - 更新阶段脚本
- `POST /api/release/pipeline-templates/{id}/preview/` - 预览模版

### 3.3 前端实现

#### 3.3.1 页面结构
- **模版列表页**: 展示所有模版，支持筛选、搜索
- **模版表单**: 创建/编辑模版
- **版本管理弹窗**: 管理模版的所有版本
- **阶段编辑弹窗**: 编辑单个阶段的脚本

#### 3.3.2 核心功能
- 模版列表支持按语言、类型、框架筛选
- 版本列表显示版本号、状态、变更日志
- 阶段编辑支持选择阶段并编辑对应脚本
- 导出功能生成 JSON 文件下载
- 导入功能支持拖拽或选择 JSON 文件

## 4. 业务流程

### 4.1 创建模版流程
1. 用户填写模版基本信息
2. 填写初始版本信息（版本号、内容、变更日志）
3. 系统创建模版记录
4. 系统创建初始版本记录，并设为最新版本
5. 返回创建成功

### 4.2 版本迭代流程
1. 用户选择某个版本点击"自动迭代"
2. 系统基于当前版本号自动递增（如 1.0.0 → 1.0.1）
3. 复制当前版本的所有内容到新版本
4. 取消其他版本的"最新"标记
5. 设置新版本为最新版本
6. 返回新版本信息

### 4.3 阶段编辑流程
1. 用户选择某个版本点击"编辑阶段"
2. 系统加载版本的阶段定义和阶段脚本
3. 用户选择要编辑的阶段
4. 用户修改阶段脚本内容
5. 系统更新 `stages_content` 字段
6. 更新版本的 `update_time` 和 `modifier`
7. 返回更新成功

### 4.4 模版复制流程
1. 用户选择某个模版点击"复制"
2. 系统生成新的模版编码（原编码 + _copy）
3. 复制模版基本信息，设置为非官方模版
4. 复制最新版本的内容，版本号重置为 1.0.0
5. 返回新模版信息

### 4.5 导入导出流程

#### 导出
1. 用户选择某个模版点击"导出"
2. 系统获取模版基本信息和最新版本信息
3. 生成 JSON 格式的配置文件
4. 浏览器下载 JSON 文件

#### 导入
1. 用户点击"导入模版"按钮
2. 选择或拖拽 JSON 文件
3. 系统解析 JSON 文件
4. 检查模版编码是否已存在
5. 创建模版和初始版本
6. 返回导入成功

## 5. 非功能需求

### 5.1 性能要求
- 模版列表加载时间 < 1s
- 版本列表加载时间 < 500ms
- 导入导出操作响应时间 < 2s

### 5.2 安全要求
- 模版编码唯一性校验
- 版本号唯一性校验（同一模版下）
- 操作权限控制（创建、编辑、删除）
- 操作日志记录（创建人、修改人、时间）

### 5.3 可用性要求
- 界面友好，操作直观
- 错误提示清晰明确
- 支持批量操作（批量导入）
- 支持搜索和筛选

## 6. 验收标准

### 6.1 功能验收
- ✅ 支持创建、编辑、删除模版
- ✅ 支持创建、查看、设置最新版本
- ✅ 支持自动版本迭代
- ✅ 支持阶段独立编辑
- ✅ 支持模版复制
- ✅ 支持模版导入导出
- ✅ 支持模版预览
- ✅ 支持版本内容查看

### 6.2 数据验收
- ✅ 模版编码唯一性
- ✅ 版本号唯一性（同一模版下）
- ✅ 最新版本标记唯一性（同一模版下只有一个最新版本）
- ✅ 软删除机制正常工作
- ✅ 操作日志完整记录

### 6.3 界面验收
- ✅ 模版列表展示完整
- ✅ 版本管理弹窗功能完整
- ✅ 阶段编辑弹窗功能完整
- ✅ 导入导出功能正常
- ✅ 错误提示友好

## 7. 后续规划

### 7.1 短期规划
- 支持模版市场，用户可以分享和下载模版
- 支持模版评分和评论
- 支持模版使用统计

### 7.2 长期规划
- 支持可视化编辑 Pipeline
- 支持模版参数化配置
- 支持模版测试和验证
- 支持模版的 Git 版本管理
- 支持模版的 AI 生成和优化

## 8. 附录

### 8.1 版本号规范
采用语义化版本规范（Semantic Versioning）：
- 格式：`主版本号.次版本号.修订号`
- 主版本号：不兼容的 API 修改
- 次版本号：向下兼容的功能性新增
- 修订号：向下兼容的问题修正

### 8.2 模版编码规范
- 格式：`{language}_{framework}_{type}`
- 示例：`java_maven_ci`、`python_django_cd`
- 全小写，使用下划线分隔
- 复制时自动添加 `_copy` 后缀

### 8.3 阶段命名规范
- 使用英文命名，首字母大写
- 常用阶段：Checkout、Build、Test、Code Analysis、Build Image、Push Image、Deploy、Health Check
- 自定义阶段需要清晰表达阶段用途
