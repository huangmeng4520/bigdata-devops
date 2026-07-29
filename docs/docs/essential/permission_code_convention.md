---
sidebar_position: 11
---

# 权限码（按钮级权限）命名规范

本文档统一前后端**按钮级权限码（RBAC 按钮权限）**的命名约定，是所有新增/修改按钮权限时必须遵循的开发规范。菜单的页面级标识（`catalog` / `menu` 类型）不在此规范约束范围内。

---

## 一、权限码格式

```
<app_label>:<model_name>:<action>
```

| 段 | 含义 | 规则 |
|----|------|------|
| `app_label` | Django app 名 | 如 `release`、`system`、`ai` |
| `model_name` | 模型类名转 snake_case | **必须下划线**，如 `CodeRepository → code_repository` |
| `action` | 操作动作 | 见下表 |

### model_name 示例

| 模型类 | 正确（下划线） | 错误写法（禁止） |
|--------|----------------|------------------|
| `CodeRepository` | `code_repository` | `code-repository`（连字符） |
| `ReleaseRecord` | `release_record` | `record`（简写） |
| `PipelineTemplate` | `pipeline_template` | `pipeline-template` |
| `EnvironmentStrategy` | `environment_strategy` | `environment-strategy` |
| `ConfigPackage` | `config_package` | `config-package` |

---

## 二、action 取值与后端 DRF action 映射

| DRF action | 按钮 action | 含义 |
|------------|-------------|------|
| `list` / `retrieve` | `query` | 查询 / 查看 |
| `create` | `create` | 新增 |
| `update` / `partial_update` | `edit` | 编辑 |
| `destroy` | `delete` | 删除 |
| 自定义 action | 见名知义，可用连字符 | 如 `sync-gitlab`、`sync-jenkins`、`import`、`trigger`、`approve` |

> **注意**：`<action>` 段允许连字符（如 `release:application:sync-jenkins`），但 `<model_name>` 段**永远下划线**，禁止连字符或简写。

---

## 三、后端自动推导规则（权威来源）

后端在 `utils/custom_model_viewSet.py` 与 `utils/permissions.py` 中按以下规则自动推导接口所需权限码。前端按钮码必须与之一致，否则按钮被隐藏且接口返回 `403`：

```python
# model_name 由模型类名转 snake_case（下划线）
model_name = camel_to_snake(view.queryset.model.__name__)   # CodeRepository -> code_repository
action_map = {
    'create': 'create',
    'update': 'edit', 'partial_update': 'edit',
    'destroy': 'delete',
    'list': 'query', 'retrieve': 'query',
}
required_code = f"{app_label}:{model_name}:{action_map[action]}"
```

**结论**：按钮权限码的 `<model_name>` 段一律下划线；禁止使用连字符（如 `code-repository`）或简写（如 `record` 代替 `release_record`）。

---

## 四、前端使用规范

- 操作按钮用 `v-auth` 指令或 `:auth` / `auth` 绑定，值必须是权限码数组，且元素与数据库 `Menu(type=button).auth_code` **精确匹配**（前端 `hasPermission` 为精确匹配，不做任何转换）：

  ```html
  <a-button v-auth="['release:code_repository:create']">新增仓库</a-button>
  <a-button :auth="['release:code_repository:delete']">删除</a-button>
  ```

- 条件显示用 `hasPermission('release:release_record:query')`，参数同样必须是规范下划线码。

- 禁止在 `<model_name>` 段使用连字符或简写。

- 前端权限集来自登录接口返回的 `permissions`（按钮 `auth_code` 列表），修改权限后需**刷新页面**重新拉取。

---

## 五、数据库 / 种子命令

- 按钮（`type=button`）的 `auth_code` 由 `backend/system/management/commands/setup_release_roles.py` 生成，模型名统一下划线。
- 运维（`ops`）角色绑定**全部导航菜单 + 全部按钮**（字面“所有权限”），数据范围 `data_scope='all'`。
- 新增按钮时必须保证 `model_name` 为下划线，避免与前端不一致。

---

## 六、常见错误与排查

| 现象 | 原因 | 修复 |
|------|------|------|
| 按钮不显示 | 前端用 `release:code-repository:create`（连字符），数据库是 `release:code_repository:create` | 前端改为下划线 |
| 按钮不显示 | 前端用 `release:record:*`，数据库是 `release:release_record:*` | 前端 `record` → `release_record` |
| 接口 `403` | 同上，权限码不匹配 | 统一为下划线规范码 |

---

## 七、自动化校验（提交前 / CI）

项目提供校验命令，扫描前端所有权限码并检查是否都存在于数据库按钮表中：

```bash
cd backend
python manage.py check_permission_codes
```

- 输出所有“前端引用但数据库缺失”的权限码及文件位置；
- 存在缺失时退出码为 `1`，可用于 CI 卡点；
- 无任何缺失时退出码为 `0`。

---

## 八、新增按钮检查清单

- [ ] 确定后端模型类名，推导下划线 `model_name`
- [ ] 规划权限码 `app:snake_model:action`（`model` 段下划线）
- [ ] 数据库按钮（`Menu.type=button`）`auth_code` 与之一致
- [ ] 前端 `v-auth` / `hasPermission` 使用同一码（精确匹配）
- [ ] 运行 `python manage.py check_permission_codes` 无缺失
- [ ] 刷新页面验证：按钮可见、接口返回 `200`（或校验错误，而非 `403`）
