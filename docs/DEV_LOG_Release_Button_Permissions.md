# 发布模块按钮权限体系 — 开发记录与排查手册

> 日期：2026-07-30
> 分支：`feature/cmdb`
> 主题：发布(release)模块后端按钮权限校验补齐 + 前端"创建模块"按钮越权显示问题排查修复

---

## 一、背景

发布模块多数视图集此前**没有后端按钮权限校验**：`CustomModelViewSet.get_permissions()` 仅在视图显式设置 `required_permission` 时才追加 `HasButtonPermission`，否则完全依赖视图自身的 `permission_classes`。而大部分视图只挂了 `DataPermissionMixin`（数据隔离），写操作对任何登录用户放行。

此前已修复 `ModuleViewSet`（加 `HasMutateButtonPermission`），本次将同样修复推广到发布模块所有视图集，并排查了一个前端按钮越权显示问题。

## 二、权限机制速查（排查必读）

### 后端

- **权限类**：`backend/utils/permissions.py`
  - `HasButtonPermission`：按 action 推断按钮码后校验；**若按钮码未在菜单(Menu, type=button)登记则直接放行**。
  - `HasMutateButtonPermission`：同上，但只对写操作(POST/PUT/PATCH/DELETE)校验，读操作放行按钮码检查（仍受 query 码机制影响，见下）。
  - action → 按钮码后缀推断规则：`create→create`、`update/partial_update→edit`、`destroy→delete`、`list/retrieve→query`。
  - 按钮码格式：`{app}:{model}:{action}`，如 `release:module:create`。
- **基类**：`backend/utils/custom_model_viewSet.py` 的 `CustomModelViewSet.get_permissions()`
  - 会对所有动作自动追加 `HasButtonPermission`（含 `list→query`）；**读操作是否被拦取决于 query 码是否已登记**。`release:*:query` 码已登记，因此发布模块读操作也需要角色授权。
  - 自定义 `@action` 不走推断，需在视图 `get_permissions()` 中设置 `self.required_permission`。
- **超管**：`is_superuser=True` 绕过全部按钮校验。
- **默认权限**：`settings.py` 中 `DEFAULT_PERMISSION_CLASSES = AllowAny`，各视图自行控制。

### 前端

- **权限码来源**：登录时 `fetchUserInfo()` 将 `userInfo.permissions`（真实按钮码）写入 `accessStore.accessCodes`。
  - ⚠️ 历史坑：`store/auth.ts` 曾并行调用 `getAccessCodesApi()`（后端 `/system/codes/` 是硬编码 mock `AC_xxx`）**覆盖**真实码，导致登录后（不刷新页面）所有 `auth` 判断失效。已于本次移除。
- **判断函数**：`#/utils/permission.ts` 的 `hasPermission(code)` — 精确字符串匹配，**无 `edit`/`update` 归一**。
- **表格操作列**：`adapter/vxe-table.ts` 的 `CellOperation` 渲染器。各页面 `data.ts` 中用 `op(authCode, opt)` 包装按钮，无权限时返回 `false`。
  - ⚠️ 历史坑：渲染器此前不过滤 `false` 项、也不解析 `auth: []` 属性。已于本次加固（过滤 falsy 项 + 支持 `auth` 数组过滤）。

## 三、本次改动清单

### 1. 后端视图：补齐 `HasMutateButtonPermission`

| 文件 (backend/release/views/) | 视图集 | 说明 |
|---|---|---|
| `application.py` | `ApplicationViewSet` | 新增 `permission_classes = [HasMutateButtonPermission]` |
| `code_repository.py` | `CodeRepositoryViewSet` | 同上 |
| `project.py` | `ProjectViewSet` | 同上 |
| `application_pipeline.py` | `ApplicationPipelineConfigViewSet` | 同上 |
| `cd_config_export.py` | `CDConfigExportViewSet` | 同上 |
| `environment_strategy.py` | `EnvironmentStrategyViewSet` | 同上 |
| `config_package.py` | `ConfigPackageViewSet` | 同上 |
| `pipeline_template.py` | `PipelineTemplateViewSet` + `PipelineTemplateVersionViewSet` | 同上 |
| `release.py` | `ReleaseRecordViewSet`、`ApprovalRuleViewSet` | `[IsAuthenticated, HasMutateButtonPermission]` 叠加 |

`ReleaseRecordViewSet` 额外新增 `get_permissions()` 覆盖，为自定义动作绑定按钮码：

```python
RECORD_ACTION_PERMS = {
    'trigger': 'release:release_record:trigger',
    'cancel': 'release:release_record:cancel',
    'approve': 'release:release_record:approve',
    'reject': 'release:release_record:reject',
    'retry': 'release:release_record:retry',
    'ai_analysis': 'release:release_record:ai_analysis',
}
```

### 2. 按钮码登记（让基类真正拦截）

文件：`backend/system/management/commands/setup_release_permissions.py`

扩展 `menus_buttons`，为以下模型登记 `create/edit/delete` 等码（挂到对应前端菜单路径）：

- `/release/application`：application(create/edit/**update**/delete)、config_package、application_pipeline_config
- `/release/code-repository`：code_repository(create/edit/**update**/delete)
- `/release/pipeline-template`：pipeline_template、pipeline_template_version
- `/release/environment-strategy`、`/release/cd-export`
- `/release/record`：release_record(create/edit/delete/trigger/cancel/approve/reject/retry/ai_analysis)、approval_rule

已执行 `python manage.py setup_release_permissions` 写入库（幂等可重复执行）。

⚠️ **edit/update 双码问题**：前端应用/代码仓库"编辑"按钮用 `release:*:update`，后端 update 动作推断 `release:*:edit`。两码均已登记，**给角色授权时需同时勾选**；后续可统一前端改用 `edit` 简化。

### 3. 前端修复（"创建模块"按钮越权显示）

**现象**：研发角色未授权 `release:module:create`，但项目列表页"创建模块"按钮可见且可创建成功。

**根因（3 层叠加）**：

1. `views/release/project/data.ts`："创建模块"按钮用 `auth: ['release:module:create']` 属性，但 `CellOperation` 渲染器不解析 `auth` → 按钮对所有人可见。
2. `views/release/module/index.vue`：跳转 `/release/module?create=1` 后 `onMounted` 无权限校验直接弹创建表单。
3. 后端旧代码未加载 `HasMutateButtonPermission`（服务未重启）→ API 放行。

**修复**：

| 文件 | 修改 |
|---|---|
| `views/release/project/data.ts` | 按钮改用 `op('release:module:create', {...})` 包装 |
| `views/release/module/index.vue` | `create=1` 弹窗前校验 `hasPermission('release:module:create')` |
| `adapter/vxe-table.ts` | `CellOperation` 过滤 falsy 项 + 通用支持 `auth: string[]` 过滤（全局生效） |
| `store/auth.ts` | 移除 `getAccessCodesApi()` mock 覆盖真实权限码的逻辑 |

## 四、验证结果（冒烟测试，11/11 通过）

用 `APIRequestFactory + force_authenticate` 在 Django shell 中实测：

| 场景 | 结果 |
|---|---|
| 无角色用户：GET/POST/DELETE 各视图 | 全部 403（query 码已登记，读也需授权） |
| 仅授 `release:application:query`：GET list | 200 放行 |
| 仅授 query：POST create / DELETE | 403 拦截 |
| 超管：POST create | 400（过权限层，进参数校验） |
| 超管：release_record approve(不存在id) | 404（过权限层，进业务查找） |
| dev_test(研发角色)：module POST create | 403 无操作权限 |

## 五、遗留事项 / 下次迭代

1. **角色授权**：新登记的按钮码尚未分配给业务角色，需在「角色管理」为相关角色勾选（含 query 码、edit+update 双码），否则非超管无法使用发布模块（预期安全行为）。
2. **未强校验的自定义动作**：发布(`release:application:release` 已在 `trigger_release` 函数视图显式检查)、同步 Jenkins/Harbor、代码仓库导入/同步 GitLab 等 `@action` 未设 `required_permission`，行为与之前一致；如需强校验，参照 `ReleaseRecordViewSet.RECORD_ACTION_PERMS` 模式补齐。
3. **edit/update 双码统一**：建议前端 application/code_repository 的编辑按钮码从 `update` 改为 `edit`，然后删除 `update` 冗余码。
4. **后端 `/system/codes/` mock 接口**：仍是硬编码 `AC_xxx`，前端已不再依赖，可考虑改为返回真实按钮码或下线。
5. **部署提醒**：后端改动需**重启 Django 服务**生效；前端需重新构建。

## 六、快速排查指南（下次遇到类似问题）

**症状：按钮不该显示却显示了**
1. 查页面 `data.ts`：按钮是否用 `op(authCode, ...)` 包装？直接写 `auth: []` 的旧写法现在也支持了，但优先用 `op()`。
2. 查用户实际权限码：浏览器控制台 `accessStore.accessCodes`，或后端查角色 `role.permissions`。
3. 确认没有 mock 覆盖（`store/auth.ts` 已修，警惕回归）。

**症状：API 不该放行却放行了**
1. 视图是否有 `HasMutateButtonPermission` / `required_permission`？
2. 按钮码是否已在菜单登记？未登记 = 直接放行（`HasButtonPermission` 的设计）。查询：
   ```python
   Menu.objects.filter(type='button', auth_code='release:xxx:yyy')
   ```
3. 用户是否 `is_superuser`（绕过所有校验）？
4. **服务是否重启加载了新代码**？（本次事故直接原因）

**快速实测模板**（Django shell）：
```python
from rest_framework.test import APIRequestFactory, force_authenticate
from system.models import User
from release.views.module import ModuleViewSet
factory = APIRequestFactory()
u = User.objects.get(username='xxx')
view = ModuleViewSet.as_view({'post': 'create'})
req = factory.post('/fake/', {'name': 't'}, format='json')
force_authenticate(req, user=u)
print(view(req).status_code)  # 期望 403
```

---

## 七、附加变更（同日）：流水线模板编辑界面去除 Jenkinsfile 字段

> 主题：模板编辑表单不再处理 Jenkinsfile 内容，统一交给「版本管理」维护。

### 背景
模板编辑表单 `pipelineTemplate/modules/form.vue` 原在**创建模式**下暴露 5 个"模板内容（第一版本）"字段：
`version`、`environment`（环境变量）、`content`（Jenkinsfile 不含 environment）、`change_log`、`is_latest`，
用于在创建模板时一并生成第一版本。

排查发现两个问题：
1. `data.ts` 的 `useSchema(isEdit)` 中这些字段仅在 `if (!isEdit)` 时加入，因此**编辑模式下根本不渲染** `environment`/`content` —— 用户在编辑界面看不到 Jenkinsfile 内容并非"读取了最新版本"，而是字段压根没渲染，且 `loadData` 回填的模板主记录也不含 `content`（`content` 属于 `PipelineTemplateVersion`）。
2. `PipelineTemplate` 模型及序列化器本就不含 `content`/`environment`，第一版本创建本就是前端职责。

决策：**模板编辑界面只维护元信息（名称/编码/语言/框架/状态等），Jenkinsfile 内容完全由「版本管理」标签页维护**（编辑 Environment / 编辑 Stage / 创建版本）。

### 改动清单
| 文件 | 改动 |
|------|------|
| `web/.../pipelineTemplate/data.ts` | `useSchema` 删除 `if (!isEdit)` 块（去掉 `version`/`environment`/`content`/`change_log`/`is_latest` 及"模板内容"分隔符）；创建与编辑现在共用同一份纯元信息 schema |
| `web/.../pipelineTemplate/modules/form.vue` | ① 删除本地 `extractEnvironment`/`mergeEnvironment` 函数与 `handleValuesChange`（不再需要拆分/合并显示）；② `onOpenChange` 创建模式初始化不再注入版本内容字段；③ `handleSubmit` 编辑分支只提交元信息，**不再传 `content`**；④ 创建分支改为调用 `getDefaultContent(values.language)` **自动生成默认 `1.0.0` 版本**，无需用户填写 Jenkinsfile |

### 影响与注意
- 编辑模板不会再触碰 Jenkinsfile 内容（内容保持不变），符合"编辑从版本管理进行"。
- 新建模板后自动带默认 `1.0.0` 版本，进入版本管理即可直接「编辑 Environment / 编辑 Stage / 复制最新版本」，不会因去除字段而变成无版本。
- **后端无需改动**（`PipelineTemplate` 模型本无 `content`/`environment` 字段）。
- 版本管理的 `extractEnvironment`/`updateEnvironment` 来自 `utils/jenkinsfileParser.ts`（独立实现，tokenizer 精确匹配花括号），本次改造**未受影响**，仍正常用于各版本的 environment 块读写。
- lint 检查通过，无残留引用。

---

## 八、版本管理交互优化（同日）

> 目标：提升流水线模板「版本管理」的前端交互体验，清理后端死代码。

### 现状梳理（versions.vue + pipeline_template.py）
- 版本列表（时间线卡片）：查看详情 / 设为最新 / 编辑Stage / 编辑Environment / 迭代版本。
- 新建版本：整页 `viewMode='create'` 表单（版本号/变更说明/Jenkinsfile），可「从最新版本复制」。
- 版本详情抽屉：查看/编辑统一表单（查看禁用、编辑启用、右上角保存、保存关闭）。
- 编辑 Stage / Environment：均**基于所选版本生成新版本**（带 nextVersion，留痕），不覆盖原版本。
- 版本对比弹窗：选两个版本行级 diff。
- 后端：`PipelineTemplateViewSet`（versions/create_version/preview/copy/export_config/import_config）+ `PipelineTemplateVersionViewSet`（set_latest/auto_version/update_stage）。

### 优化清单
| 项 | 改动 |
|----|------|
| 清理调试日志 | 移除 handleEditStage / handleSaveStage 中的 console.log/error |
| 操作防重复 | 创建版本/复制最新/设为最新/自动迭代 加 `modalApi.lock()`；详情保存 `detailSaving`；Stage `stageSaving`(confirm-loading)；Environment `envSaving`(confirm-loading) |
| 新建版本默认填充 | showCreateForm 默认带最新版本完整 Jenkinsfile 内容，减少空白起步 |
| 对比快捷 | 对比弹窗新增「与上一版本对比」按钮（compareWithPrev 自动选相邻版本） |
| 后端清理 | 删除未被前端调用的 `update_stage` 死代码（其逻辑只改 stages_content 字典、不重写 content，与前端实际逻辑不符） |

### 验证
- 前端 lint 通过（0 错误）；后端 `manage.py check` 通过（0 issues）。
- 复用了上一轮已完成的「详情抽屉统一表单 + 右上角保存 + 保存关闭」。

### 待确认（产品决策，未实施）
1. 是否增加「删除版本」功能（需保护 latest 版本不被删）。
2. 详情抽屉「编辑」= 覆盖当前版本；列表「编辑Stage/Environment」= 派生新版本。两者语义不同，是否需在 UI 上提示区分？
3. 新建版本是否改为 Drawer 弹窗（更轻量，保留列表上下文）而非整页切换。
4. 后端版本号格式校验（当前仅判重）。
