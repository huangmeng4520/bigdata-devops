# Bigdata-DevOps 开发规范

## 1. API 响应格式规范

### 后端响应格式

所有 API 响应必须使用 `_build_response` 方法包装，返回统一格式：

```python
# 正确 ✅
def my_action(self, request, pk=None):
    data = {...}
    return self._build_response(data=data, message="ok")

# 错误 ❌
def my_action(self, request, pk=None):
    return Response(serializer.data)  # 格式不一致
```

**标准响应格式**：
```json
{
    "code": 0,
    "message": "ok",
    "data": { ... }
}
```

### 前端响应处理

`requestClient` 配置了自动解包，当 `code=0` 时直接返回 `data` 字段：

```typescript
// 后端返回: { code: 0, data: { id: 1, name: "test" } }
// 前端收到: { id: 1, name: "test" }

const res = await getDetail(id);
console.log(res.id);  // 直接访问，不是 res.data.id
```

### 列表接口格式

分页列表返回格式：
```json
{
    "code": 0,
    "data": {
        "total": 100,
        "items": [...]
    }
}
```

前端处理：
```typescript
const res = await getList(params);
tableData.value = res.items || [];
pagination.total = res.total || 0;
```

---

## 2. 前端组件规范

### 组件导入

必须显式导入使用的组件，不能直接使用 `a-` 前缀：

```vue
<script setup>
// 正确 ✅
import { Button, Divider, Input, Select, Tag } from 'ant-design-vue';
</script>

<template>
  <!-- 正确 ✅ -->
  <Divider />
  <Input v-model:value="form.name" />
  
  <!-- 错误 ❌ - 未导入会导致渲染失败 -->
  <a-divider />
  <a-input v-model:value="form.name" />
</template>
```

### Modal 组件使用

`useVbenModal` 的 `onConfirm` 回调必须在调用前定义：

```vue
<script setup>
// 正确 ✅ - 函数定义在前
function handleConfirm() {
  modalApi.close();
  return true;
}

const [Modal, modalApi] = useVbenModal({
  onConfirm: handleConfirm,
});

// 错误 ❌ - 函数未定义就使用
const [Modal, modalApi] = useVbenModal({
  onConfirm: handleConfirm,  // handleConfirm 未定义
});

function handleConfirm() {
  modalApi.close();
}
</script>
```

### Modal 属性

避免使用可能导致内容禁用的属性：

```vue
<!-- 避免 ❌ -->
<Modal :loading="submitting" :footer="true">

<!-- 推荐 ✅ -->
<Modal title="标题" width="600px">
  <Spin :spinning="loading">
    <!-- 内容 -->
  </Spin>
</Modal>
```

---

## 3. 表单数据处理规范

### 空值处理

后端 `allow_null=True` 只接受 `null`，不接受空字符串：

```python
# 后端序列化器
approval_type = serializers.CharField(allow_null=True, required=False)
```

```typescript
// 前端提交前清理空字符串
const submitData: any = {
  name: form.name,
  remark: form.remark || '',
};

// 只有有值时才添加可选字段
if (form.approval_type) {
  submitData.approval_type = form.approval_type;
}
```

### 默认值设置

```typescript
// 推荐 ✅ - 明确默认值
const formData = ref({
  branch: '',
  environment: '',
  version: '',
  approval_type: '',  // 空字符串，提交时需过滤
  require_approval: false,
});
```

---

## 4. 后端 ViewSet 规范

### 自定义 Action

所有自定义 action 必须使用 `_build_response`：

```python
@action(detail=True, methods=['get'])
def logs(self, request, pk=None):
    """获取构建日志"""
    logs = self.get_object().build_logs.all()
    serializer = self.get_serializer(logs, many=True)
    # 正确 ✅
    return self._build_response(data=serializer.data, message="ok")
    # 错误 ❌
    # return Response(serializer.data)
```

### 权限控制

```python
@action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
def approve(self, request, pk=None):
    pass
```

---

## 5. Celery 任务规范

### 任务结构

```python
@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def my_task(self, param_id: int):
    """任务描述"""
    logger.info(f"[Celery] 开始执行任务: param_id={param_id}")
    
    try:
        # 业务逻辑
        result = do_something(param_id)
        logger.info(f"[Celery] 任务完成: result={result}")
        return {"success": True, "result": result}
    except Exception as e:
        logger.exception(f"[Celery] 任务异常: {e}")
        # 重试
        raise self.retry(exc=e)
```

### 外部服务调用

优先检查资源是否存在，再执行操作：

```python
# 检查 Jenkins Job 是否存在
if not jenkins.job_exists(job_name, folder):
    logger.error(f"Job 不存在: {job_name}")
    return {"success": False, "error": "Job 不存在"}

# 检查 Job 是否需要参数
is_parametrized = jenkins.check_job_has_parameters(job_path)
```

---

## 6. 日志规范

### 构建日志存储

发布完成后自动存储 Jenkins 构建日志：

```
触发构建 → poll_build_status 轮询 → 构建完成 → fetch_build_log 拉取日志 → 存储到 release_build_log 表
```

### 日志查询

```sql
-- 查询发布记录的构建日志
SELECT * FROM release_build_log WHERE release_id = ? ORDER BY create_time;
```

---

## 7. 错误处理规范

### 前端错误处理

```typescript
try {
  const res = await api.getData();
  // 处理数据
} catch (error: any) {
  console.error('操作失败', error);
  message.error(error?.response?.data?.error || '操作失败');
}
```

### 后端错误处理

```python
try:
    result = do_something()
except SomeException as e:
    logger.exception(f"操作失败: {e}")
    return self._build_response(
        code=1, 
        message=str(e), 
        status=status.HTTP_400_BAD_REQUEST
    )
```

---

## 8. 数据库查询规范

### 关联查询

使用 `select_related` 和 `prefetch_related` 优化查询：

```python
# 正确 ✅
queryset = ReleaseRecord.objects.select_related(
    'application', 'application__project', 'application__module'
).all()

# 避免 N+1 查询
for record in queryset:
    print(record.application.name)  # 不会额外查询
```

### 软删除

```python
# 使用软删除字段过滤
queryset = Model.objects.filter(is_deleted=False)
```

---

## 9. 命名规范

### 前端文件命名

```
views/
  release/
    application/          # 功能模块目录
      index.vue          # 列表页
      data.ts            # 数据定义
      modules/           # 子组件
        form.vue         # 表单弹窗
        ReleaseModal.vue # 发布弹窗
```

### API 文件命名

```typescript
// api/release/index.ts    - 应用相关 API
// api/release/record.ts   - 发布记录 API
// api/release/deployment.ts - 部署相关 API
```

### 后端文件命名

```
backend/release/
  models.py           # 数据模型
  serializers.py      # 序列化器
  views/
    __init__.py
    release.py        # 发布相关视图
    statistics.py     # 统计相关视图
  tasks.py            # Celery 任务
  services/           # 业务服务
    jenkins_service.py
```

---

## 10. 常见问题 Checklist

开发时检查以下问题：

- [ ] 后端 API 是否使用 `_build_response` 包装响应
- [ ] 前端是否正确处理 `requestClient` 自动解包的响应
- [ ] 组件是否正确导入（不使用未导入的 `a-` 组件）
- [ ] `useVbenModal` 的回调函数是否在调用前定义
- [ ] 表单提交前是否过滤空字符串（后端只接受 `null`）
- [ ] Celery 任务是否有完善的日志和错误处理
- [ ] 数据库查询是否使用 `select_related` 优化
