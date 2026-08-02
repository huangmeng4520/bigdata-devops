# GitLab 项目导入修复与优化

> 日期: 2026-08-02

## 概述

修复 GitLab 项目批量导入功能中的三个核心问题：弹窗组件渲染失败、批量导入超时、部分仓库（长路径/长名称）无法导入。

## 问题清单

### 1. 导入弹窗组件不渲染

- **现象**: 弹窗打开后不显示任何数据，控制台报 `Failed to resolve component: a-input-search / a-tag / a-pagination`
- **根因**: `useVbenModal` 的 `connectedComponent` 模式下，`unplugin-vue-components` 自动导入不生效，模板中 `a-` 前缀组件全部解析失败
- **修复**: `importGitlabModal.vue` - 手动 import `Input`、`Tag`、`Pagination`，模板替换为 `Input.Search`、`Tag`、`Pagination`

```typescript
// 修复前: 依赖自动导入 (不生效)
<a-input-search /> <a-tag /> <a-pagination />

// 修复后: 手动 import + 直接使用
import { Input, Pagination, Tag } from 'ant-design-vue';
<Input.Search /> <Tag /> <Pagination />
```

### 2. 批量导入前端超时

- **现象**: 前端请求超时，但后端实际导入成功
- **根因**: `import_gitlab_projects` 是同步接口，每个项目调用 `gitlab.get_project()` 发起一次 HTTP 请求，批量导入耗时长
- **修复**: 将批量导入改为 Celery 异步任务

| 文件 | 变更 |
|------|------|
| `backend/release/views/code_repository.py` | `import_gitlab_projects` 改为提交 Celery 任务后秒级返回 `task_id` |
| `backend/release/tasks.py` | 新增 `import_gitlab_projects_batch` Celery 任务，后台逐项导入 |
| `web/.../codeRepository.ts` | `importGitLabProjects` 改用 `baseRequestClient` + `timeout: 300000` 兜底 |
| `web/.../importGitlabModal.vue` | 适配异步返回，提示改为"正在后台处理" |

### 3. 部分仓库无法导入

- **现象**: 仓库路径类似 `expert-platform-for-project-management`(45字符) 或名称类似 `Expert Platform for Project Management`(41字符) 无法导入
- **根因**:
  - `CodeRepository.code` 字段 `max_length=32`，仓库路径超出限制导致 `IntegrityError`
  - `CodeRepository.name` 字段 `max_length=64`，留余量不足
  - `GitLabService.get_project()` 静默吞掉异常返回 `None`，无法定位具体失败原因

- **修复**:

| 文件 | 变更 |
|------|------|
| `backend/release/models.py` | `code` 32→256, `name` 64→256 |
| `backend/release/migrations/0021_alter_coderepository_code_length.py` | code 字段扩容迁移 |
| `backend/release/migrations/0022_alter_coderepository_name_length.py` | name 字段扩容迁移 |
| `backend/release/services/gitlab_service.py` | `get_project()` 新增 `raise_on_error` 参数，设为 `True` 时透传异常 |
| `backend/release/tasks.py` | Celery 任务捕获 `DevOpsException` 记录详细错误信息 |

## 架构变更

### 批量导入流程 (修改后)

```
前端                        后端                      Celery
 │                           │                          │
 ├── POST import_gitlab ────>│                          │
 │   (data: selected_ids)    │                          │
 │                           ├── 参数校验                │
 │                           ├── 过滤已导入              │
 │                           ├── .delay(items,user) ───>│
 │                           │                          ├── 遍历 items
 │   <── {task_id, message} ─│                          │   ├── get_project(raise_on_error=True)
 │                           │                          │   ├── 路径/名称长度检查
 │   message.success("后台处理中")                        │   ├── 匹配 project/module
 │   emit('success')         │                          │   ├── create / restore
 │                           │                          │   └── 记录详细 error
 │                           │                          │
 │  (用户刷新列表，数据已就绪)  │                          │
```

### 错误传递链路 (修改后)

```
GitLab API 异常 (403/404/500...)
  → _handle_error() → DevOpsException(message)
    → get_project(raise_on_error=True) → 透传 DevOpsException
      → import_gitlab_projects_batch → catch → 记录具体错误
        → 前端不阻塞（异步），Celery 日志完整记录
```

## 部署注意事项

```bash
# 1. 数据库迁移
cd backend
python manage.py migrate release  # 执行 0021 + 0022

# 2. 重启 Celery Worker（必须！新任务需要重新加载）
pkill -f "celery worker"
celery -A backend worker -l info &

# 3. 重启后端
# 4. 前端重新构建
```

## GitLab API 版本兼容

经确认，本地测试环境 GitLab 18.7 与生产环境 GitLab 16.4 在 `api/v4` 的 `page`/`per_page`/`X-Total` 等分页参数上完全一致，无需版本适配。

## 涉及文件清单

| 文件 | 操作 |
|------|------|
| `backend/release/models.py` | `code` 32→256, `name` 64→256 |
| `backend/release/services/gitlab_service.py` | `get_project` 增加 `raise_on_error` 参数 |
| `backend/release/views/code_repository.py` | 批量导入改为 Celery 异步调用 |
| `backend/release/tasks.py` | 新增 `import_gitlab_projects_batch` 任务 |
| `backend/release/migrations/0021_*.py` | code 字段扩容迁移 |
| `backend/release/migrations/0022_*.py` | name 字段扩容迁移 |
| `web/.../api/release/codeRepository.ts` | API 函数超时 + 响应适配 |
| `web/.../views/release/codeRepository/modules/importGitlabModal.vue` | 组件 import + 异步响应 |
