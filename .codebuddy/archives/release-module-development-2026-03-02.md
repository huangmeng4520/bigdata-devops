# 发布模块开发记录

**开发日期**: 2026-03-02
**分支**: feature/cmdb
**开发者**: AI Assistant

---

## 一、功能概述

本次开发完善了 **应用发布管理** 模块，实现了从应用发布到构建日志查看的完整流程。

### 功能架构

```
┌─────────────────────────────────────────────────────────────┐
│                      发布管理模块                            │
├─────────────────────────────────────────────────────────────┤
│  应用管理          │  发布记录           │  构建日志         │
│  ├─ 应用列表       │  ├─ 发布记录列表    │  ├─ 终端风格显示  │
│  ├─ 发布弹窗       │  ├─ 状态筛选        │  ├─ 行号显示      │
│  │  ├─ 分支选择    │  ├─ 操作按钮        │  ├─ 关键词高亮    │
│  │  ├─ 环境选择    │  │  ├─ 查看日志    │  └─ 自动存储      │
│  │  └─ 版本填写    │  │  ├─ 重试构建    │                   │
│  └─ 同步到Jenkins  │  │  └─ 取消发布    │                   │
│                    │  └─ 分页查询        │                   │
├─────────────────────────────────────────────────────────────┤
│                     后端服务层                               │
│  ├─ ReleaseRecordViewSet    - 发布记录管理                  │
│  ├─ JenkinsService          - Jenkins API 封装              │
│  ├─ Celery Tasks            - 异步任务处理                  │
│  │   ├─ trigger_jenkins_build - 触发构建                    │
│  │   ├─ poll_build_status     - 轮询状态                    │
│  │   └─ fetch_build_log       - 拉取日志                    │
│  └─ ReleaseBuildLog         - 构建日志存储                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 二、核心功能实现

### 2.1 发布弹窗功能

**文件位置**: `web/apps/web-antd/src/views/release/application/modules/ReleaseModal.vue`

**功能点**:
- 分支手动输入，默认值来自应用的 `build_branch` 字段
- 环境选择显示配置状态（已配置/未配置/需审批）
- 版本号可选填写
- 发布说明支持

**关键逻辑**:

```typescript
// 环境配置状态判断
const env = {
  code: 'dev',
  name: '开发环境',
  has_ci_config: true,      // 是否有 CI 配置
  requires_approval: false, // 是否需要审批
  pipeline_mode: 'integrated' // 流水线模式
};
```

**API 调用**:
```typescript
// 获取应用环境配置
GET /api/admin/release/application/{id}/environments/

// 触发发布
POST /api/admin/release/application/{id}/release/
{
  branch: 'main',
  environment: 'test',
  version: '1.0.0',
  remark: '发布说明'
}
```

---

### 2.2 发布记录列表

**文件位置**: `web/apps/web-antd/src/views/release/record/index.vue`

**功能点**:
- 发布记录列表展示（应用、环境、状态、构建号等）
- 多条件筛选（应用名、环境、状态、发布人、时间范围）
- 操作按钮（查看日志、重试、取消）

**数据格式**:
```typescript
interface ReleaseRecord {
  id: number;
  application_name: string;
  branch: string;
  environment: string;
  environment_display: string;
  status: string;
  status_display: string;
  jenkins_build_number: number;
  jenkins_build_url: string;
  jenkins_build_status: string;
  jenkins_build_duration: number;
  released_by: string;
  create_time: string;
}
```

---

### 2.3 构建日志功能

**文件位置**: `web/apps/web-antd/src/views/release/record/modules/BuildLogModal.vue`

**功能点**:
- 终端风格日志显示（macOS 风格头部）
- 行号显示，便于定位
- 关键词高亮（ERROR/WARNING/SUCCESS/Pipeline）
- 自动刷新（构建中状态）
- 日志自动存储到数据库

**日志存储表**: `release_build_log`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BigAutoField | 主键 |
| release | ForeignKey | 关联发布记录 |
| log_content | TextField | 日志内容 |
| log_type | CharField | 日志类型 |

---

### 2.4 Jenkins 构建集成

**文件位置**: `backend/release/services/jenkins_service.py`

**功能点**:
- Jenkins API 封装
- 支持 Folder 层级 Job
- 自动检测参数化构建
- 构建状态轮询
- 日志拉取

**关键方法**:
```python
class JenkinsService:
    def job_exists(name, folder) -> bool       # 检查 Job 是否存在
    def trigger_build(name, folder, params)    # 触发构建
    def get_build_info(name, build_number)     # 获取构建信息
    def get_build_console_output(...)          # 获取控制台输出
    def _check_job_has_parameters(job_path)    # 检查是否参数化
```

---

### 2.5 Celery 异步任务

**文件位置**: `backend/release/tasks.py`

**任务流程**:
```
trigger_jenkins_build (触发构建)
        ↓
poll_build_status (轮询状态，每 10 秒)
        ↓
构建完成？
   ├── 是 → fetch_build_log → 存储日志
   └── 否 → 继续轮询
```

**关键任务**:
```python
@shared_task
def trigger_jenkins_build(release_id: int):
    """触发 Jenkins 构建"""
    # 1. 获取应用配置（优先环境配置，其次全局 CI Job）
    # 2. 检查 Job 是否存在
    # 3. 检测参数化构建
    # 4. 触发构建
    # 5. 启动状态轮询

@shared_task
def poll_build_status(release_id: int):
    """轮询构建状态"""
    # 1. 获取构建信息
    # 2. 判断是否完成
    # 3. 更新发布记录状态
    # 4. 触发日志拉取

@shared_task
def fetch_build_log(release_id: int):
    """拉取并存储构建日志"""
    # 1. 获取 Jenkins 控制台输出
    # 2. 存储到 release_build_log 表
```

---

## 三、Bug 修复记录

### 3.1 前端 API 响应处理

**问题**: 前端无法正确处理后端返回的数据格式

**原因**: 
- 后端返回 `{code: 0, data: {...}}` 格式
- `requestClient` 自动解包返回 `data` 字段
- 前端代码使用了错误的数据访问路径

**修复**:
```typescript
// 错误 ❌
tableData.value = res.results || [];

// 正确 ✅
tableData.value = res.items || [];
pagination.total = res.total || 0;
```

---

### 3.2 组件导入问题

**问题**: 使用未导入的组件导致渲染失败

**原因**: 直接使用 `a-divider` 等未导入的组件

**修复**:
```vue
<script setup>
// 显式导入组件
import { Button, Divider, Input, Select, Tag } from 'ant-design-vue';
</script>

<template>
  <Divider />  <!-- 使用导入的组件 -->
</template>
```

---

### 3.3 Modal 回调函数定义顺序

**问题**: `useVbenModal` 的 `onConfirm` 回调未定义就使用

**原因**: 函数声明提升不适用于传递给对象属性的函数引用

**修复**:
```typescript
// 正确 ✅ - 函数定义在前
function handleConfirm() {
  modalApi.close();
  return true;
}

const [Modal, modalApi] = useVbenModal({
  onConfirm: handleConfirm,
});
```

---

### 3.4 表单空值处理

**问题**: 后端 `allow_null=True` 只接受 `null`，不接受空字符串

**原因**: 前端表单默认值为空字符串 `''`

**修复**:
```typescript
// 提交前清理空字符串
const submitData: any = {
  branch: form.branch,
  environment: form.environment,
};

// 只有有值时才添加可选字段
if (form.approval_type) {
  submitData.approval_type = form.approval_type;
}
```

---

### 3.5 Jenkins 参数化构建

**问题**: 触发构建返回 400 错误

**原因**: Job 没有定义参数，但调用了 `buildWithParameters`

**修复**:
```python
def trigger_build(self, name, folder, parameters):
    # 先检查 Job 是否是参数化构建
    is_parametrized = self._check_job_has_parameters(path)
    
    if is_parametrized and parameters:
        endpoint = f"{path}/buildWithParameters?{param_str}"
    else:
        endpoint = f"{path}/build"
```

---

### 3.6 后端 API 响应格式一致性

**问题**: 自定义 action 返回格式不一致

**原因**: 直接使用 `Response(serializer.data)` 而非 `_build_response`

**修复**:
```python
@action(detail=True, methods=['get'])
def logs(self, request, pk=None):
    serializer = self.get_serializer(logs, many=True)
    # 使用 _build_response 保持格式一致
    return self._build_response(data=serializer.data, message="ok")
```

---

## 四、数据库变更

### 4.1 新增表

**release_record** - 发布记录
```sql
CREATE TABLE release_record (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    application_id BIGINT,
    branch VARCHAR(128),
    environment VARCHAR(32),
    version VARCHAR(64),
    status VARCHAR(32) DEFAULT 'pending',
    jenkins_job_name VARCHAR(256),
    jenkins_build_number INT,
    jenkins_build_url VARCHAR(512),
    jenkins_build_status VARCHAR(32),
    jenkins_build_duration INT,
    released_by VARCHAR(64),
    create_time DATETIME,
    -- ... 其他字段
);
```

**release_build_log** - 构建日志
```sql
CREATE TABLE release_build_log (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    release_id BIGINT,
    log_content LONGTEXT,
    log_type VARCHAR(32) DEFAULT 'console',
    create_time DATETIME,
    FOREIGN KEY (release_id) REFERENCES release_record(id)
);
```

---

## 五、API 接口文档

### 5.1 应用相关

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/admin/release/application/` | GET | 应用列表 |
| `/api/admin/release/application/{id}/` | GET | 应用详情 |
| `/api/admin/release/application/{id}/environments/` | GET | 获取环境配置 |
| `/api/admin/release/application/{id}/release/` | POST | 触发发布 |

### 5.2 发布记录

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/admin/release/release-records/` | GET | 发布记录列表 |
| `/api/admin/release/release-records/{id}/` | GET | 发布记录详情 |
| `/api/admin/release/release-records/{id}/logs/` | GET | 获取构建日志 |
| `/api/admin/release/release-records/{id}/retry/` | POST | 重试构建 |
| `/api/admin/release/release-records/{id}/cancel/` | POST | 取消发布 |

---

## 六、配置说明

### 6.1 Celery 配置

```python
# backend/backend/settings.py
CELERY_BROKER_URL = 'redis://localhost:6379/1'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/1'
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 分钟超时
```

### 6.2 Jenkins 配置

```python
# 系统配置表 (system_config)
JENKINS_URL = 'http://127.0.0.1:8080/jenkins'
JENKINS_USERNAME = 'admin'
JENKINS_API_TOKEN = 'xxx'
```

---

## 七、部署说明

### 7.1 启动服务

```bash
# 后端
cd backend
python manage.py runserver

# Celery Worker
celery -A backend worker -l info

# Celery Beat (定时任务)
celery -A backend beat -l info

# 前端
cd web
pnpm run dev:antd
```

### 7.2 数据库迁移

```bash
cd backend
python manage.py migrate release
```

---

## 八、后续优化建议

1. **日志解析增强**
   - 支持 ANSI 颜色代码完整解析
   - 添加日志搜索功能
   - 支持日志下载

2. **发布流程优化**
   - 添加审批工作流
   - 支持多环境并行发布
   - 添加回滚功能

3. **监控告警**
   - 构建失败通知
   - 发布超时告警
   - 构建耗时统计

4. **性能优化**
   - 日志分页加载
   - WebSocket 实时日志推送
   - 构建日志压缩存储

---

## 九、相关文件清单

### 后端文件

```
backend/release/
├── models.py                    # 数据模型
├── serializers.py               # 序列化器
├── views/
│   ├── __init__.py
│   ├── release.py              # 发布相关视图
│   └── statistics.py           # 统计视图
├── tasks.py                     # Celery 任务
├── services/
│   └── jenkins_service.py      # Jenkins 服务
├── filters.py                   # 过滤器
├── urls.py                      # 路由配置
└── migrations/
    └── 0006_add_release_models.py
```

### 前端文件

```
web/apps/web-antd/src/
├── api/release/
│   ├── index.ts                # 应用 API
│   ├── record.ts               # 发布记录 API
│   └── deployment.ts           # 部署 API
├── views/release/
│   ├── application/
│   │   ├── index.vue           # 应用列表
│   │   ├── data.ts             # 数据定义
│   │   └── modules/
│   │       ├── form.vue        # 应用表单
│   │       └── ReleaseModal.vue # 发布弹窗
│   └── record/
│       ├── index.vue           # 发布记录列表
│       └── modules/
│           ├── BuildLogModal.vue # 日志弹窗
│           └── ApprovalModal.vue # 审批弹窗
└── router/routes/modules/
    └── release.ts              # 路由配置
```

---

**文档版本**: v1.0
**最后更新**: 2026-03-02
