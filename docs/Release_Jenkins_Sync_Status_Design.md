# 应用发布 Jenkins 同步状态逻辑重构设计文档

> 适用分支：`feature/cmdb`
> 改动提交：`722b563`
> 涉及模块：后端 `release`（models / signals / tasks / views / serializers / migration）、前端 `release/application`

---

## 1. 背景与问题

原设计中，**应用级同步状态**（`release_application.jenkins_sync_status`）与**环境级同步状态**（`release_application_pipeline_config.jenkins_sync_status`）由两条独立的写入入口维护，导致以下问题：

1. **应用级状态漂移**：批量同步（`sync_application_jenkins`）与单条同步（`sync_jenkins_config`）分别写应用级状态，两套逻辑割裂，容易不一致。
2. **「已同步」不可信**：内容修改后状态不会自动变回"待同步"，用户无法判断当前配置是否真的已同步到 Jenkins。
3. **无法表达部分成功**：一个应用多环境时，部分成功/部分失败只能用单一值表达，掩盖真实情况。
4. **未配置应用误显"待同步"**：应用下没有启用任何环境配置时，也显示"待同步"，语义错误。

---

## 2. 设计目标

- 应用级状态**不再独立存储**，而是由环境级配置**实时聚合派生**。
- 引入 `config_dirty` 脏标记，让"已同步"状态**可信**。
- 扩展状态枚举，支持"部分成功 / 未配置"等场景的精确表达。
- 通过 `post_save` 信号，环境级状态变化**自动刷新**应用级聚合状态，杜绝双入口漂移。

---

## 3. 状态枚举定义

环境级与应用级共用同一套枚举（`jenkins_sync_status`）：

| 值 | 含义 | 说明 |
|----|------|------|
| 0 | 待同步 | 初始/从未同步 |
| 1 | 同步失败 | 最近一次同步异常 |
| 2 | 已同步 | 配置已成功推送到 Jenkins |
| 3 | 同步中 | 任务执行中 |
| 4 | 待重新同步 | 曾经同步成功，但内容已变更（脏标记） |
| 5 | 未配置 | 应用下无任何启用的环境配置 |

---

## 4. 核心模型改动

### 4.1 `ApplicationPipelineConfig` 新增脏标记

```python
config_dirty = models.BooleanField(
    default=False, verbose_name="配置已变更待同步"
)
```

当生成/修改/回滚配置内容时置 `True`；同步成功后置 `False`。

### 4.2 `Application` 新增聚合派生方法 `refresh_jenkins_sync_status()`

应用级状态由该方法实时计算（扫描应用下所有**启用**的环境配置）：

```
无启用的环境配置          → 5 (未配置)
任一环境状态 == 1(失败)   → 1 (同步失败)
任一环境状态 == 3(同步中) → 3 (同步中)
有 dirty 或 任一 == 0     → 4 (待重新同步)
其余全部 == 2 且干净     → 2 (已同步)
```

同时拼接各环境明细写入 `jenkins_sync_message`，仅当状态变化时执行 `save()`，避免无谓写库。

---

## 5. 信号自动聚合

新建 `backend/release/signals.py`：

```python
@receiver(post_save, sender=ApplicationPipelineConfig)
def _on_config_save(sender, instance, **kwargs):
    instance.application.refresh_jenkins_sync_status()
```

在 `backend/release/apps.py` 的 `ready()` 中注册：

```python
from . import signals
```

> 效果：任何环境级 config 的状态/脏标记变化（含 Celery 任务中的 `config.save()`），都会**自动触发**应用级聚合状态刷新，保证两层级状态始终一致。

---

## 6. 同步任务改造 (`tasks.py`)

### 6.1 单条同步 `sync_jenkins_config`
- 三处 `.update()` 改为对象取值 + `config.save()`（让信号生效）。
- 成功分支：`config.jenkins_sync_status = 2`、`config.config_dirty = False` 后 `save()`。
- 失败分支：`jenkins_sync_status = 1` 后 `save()`。

### 6.2 批量同步 `sync_application_jenkins`
- 移除原先手动写应用级状态的逻辑。
- 改为：先将所有启用的 config 置 `3(同步中)` 并立即 `app.refresh_jenkins_sync_status()`；
- 每条环境同步完成后，依赖 `post_save` 信号自动聚合；
- 任务收尾再调用一次 `refresh_jenkins_sync_status()` 保证最终一致。

### 6.3 修复 `_sync_pipeline_config`
- 补全缺失导入 `ApplicationPipelineConfig`（原报错 `NameError` 根因）。
- 修复 `if success:` 缩进错误，补全成功/失败分支的状态回写。

---

## 7. 视图与序列化

### 7.1 `views/application_pipeline.py`
- `perform_update` / `generate` / `generate_and_sync` / `rollback` 在内容变更时置 `config_dirty = True`。
- `sync_status` 接口返回 `config_dirty` 字段。

### 7.2 `serializers.py`
`ApplicationSerializer` 新增：

```python
pipeline_sync_summary = serializers.SerializerMethodField()
```

返回各环境明细：`environment` / `environment_display` / `jenkins_sync_status` / `jenkins_sync_status_display` / `config_dirty` / `jenkins_job_name`。

---

## 8. 前端展示增强

### 8.1 `views/release/application/index.vue`
- `SYNC_STATUS_COLORS` / `SYNC_STATUS_TEXT` 增加 4（橙）、5（灰）。
- `jenkins_sync` 列模板增加 `Tooltip`，展示 `row.pipeline_sync_summary` 各环境明细（环境：状态 / 待重新同步）。

### 8.2 `PipelineConfigModal.vue`
- `getSyncTag`：当 `jenkins_sync_status === 2 && config_dirty` 时返回橙色"待重新同步"标签。
- 轮询 `pollSyncStatus` 同步 `config.config_dirty`。

---

## 9. 涉及文件清单

后端：
- `backend/release/models.py`
- `backend/release/signals.py` （新建）
- `backend/release/apps.py`
- `backend/release/tasks.py`
- `backend/release/views/application_pipeline.py`
- `backend/release/serializers.py`
- `backend/release/migrations/0020_applicationpipelineconfig_config_dirty_and_more.py` （新建）

前端：
- `web/apps/web-antd/src/views/release/application/index.vue`
- `web/apps/web-antd/src/views/release/application/modules/PipelineConfigModal.vue`
- `web/apps/web-antd/src/api/release/application.ts`
- `web/apps/web-antd/src/api/release/applicationPipeline.ts`
- `web/apps/web-antd/src/api/release/index.ts`

---

## 10. 部署与验证

1. 应用 migration：`python manage.py migrate release`。
2. 重启 **Celery Worker** 与 **Django 服务**，使 `post_save` 信号注册生效。
3. 前端重新 `dev` 热更新。
4. 验证：修改某环境配置 → 应用列表该项变"待重新同步"(橙)；点"同步 Jenkins" → 各环境状态经信号聚合，列表颜色随真实结果变化。

---

## 11. 设计收益总结

- **可信**：脏标记使"已同步"代表真实已推送。
- **一致**：信号驱动聚合，消除双入口漂移。
- **可表达**：部分成功、未配置等场景有专属状态。
- **低侵入**：聚合为纯派生逻辑，不增加额外存储维护成本。
