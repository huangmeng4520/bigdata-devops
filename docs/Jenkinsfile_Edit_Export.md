# Jenkinsfile 内容编辑和导出功能说明

## 功能概述

已实现 Jenkinsfile 流水线内容的完整编辑和导出功能。

## 1. 编辑 Jenkinsfile 内容

### 位置
**流水线模版列表 → 版本管理 → 编辑内容**

### 操作步骤
1. 进入流水线模版列表
2. 点击某个模版的"版本管理"按钮
3. 在版本列表中，点击任意版本的"编辑内容"按钮
4. 在弹出的编辑器中修改 Jenkinsfile 内容
5. 点击"确定"保存

### 功能特点
- 支持编辑任意版本的 Jenkinsfile 内容
- 使用代码编辑器（等宽字体）
- 实时保存到数据库
- 自动更新修改时间和修改人

## 2. 查看 Jenkinsfile 内容

### 位置
**流水线模版列表 → 版本管理 → 查看内容**

### 操作步骤
1. 进入版本管理
2. 点击"查看内容"按钮
3. 在只读模式下查看完整的 Jenkinsfile 内容

## 3. 导出功能

### 导出内容
导出的 JSON 文件包含：

```json
{
  "template": {
    "name": "模版名称",
    "code": "模版编码",
    "template_type": "ci",
    "language": "java",
    "language_version": "11",
    "framework": "Spring Boot",
    "description": "描述"
  },
  "version": {
    "version": "1.0.0",
    "content": "pipeline { ... }",  ← Jenkinsfile 完整内容
    "variables": {},
    "stages": [],
    "stages_content": {}
  }
}
```

### 操作步骤
1. 在模版列表中点击"导出"按钮
2. 自动下载 JSON 文件
3. 文件名格式：`{模版编码}_template.json`

### 导出的内容包括
- ✅ 模版基本信息
- ✅ 最新版本的 Jenkinsfile 完整内容
- ✅ 变量定义
- ✅ 阶段定义
- ✅ 阶段脚本内容

## 4. 导入功能

### 操作步骤
1. 点击工具栏的"导入模板"按钮
2. 选择之前导出的 JSON 文件
3. 系统自动创建模版和初始版本
4. Jenkinsfile 内容完整导入

### 注意事项
- 导入前需修改 JSON 中的 `code` 字段，避免编码重复
- 导入的版本号会重置为 JSON 中指定的版本号
- Jenkinsfile 内容完整保留

## 5. 版本管理操作列

### 可用操作
- **设为最新**：将该版本设为最新版本（仅非最新版本显示）
- **编辑内容**：编辑该版本的 Jenkinsfile 内容 ← 新增
- **自动迭代**：基于该版本自动创建新版本
- **编辑阶段**：独立编辑某个阶段的脚本
- **查看内容**：只读查看 Jenkinsfile 内容

## 6. API 接口

### 更新版本内容
```
PUT /api/release/pipeline-template-versions/{id}/
Content-Type: application/json

{
  "content": "pipeline { ... }"
}
```

### 导出模版
```
GET /api/release/pipeline-templates/{id}/export_config/
```

返回包含完整 Jenkinsfile 内容的 JSON。

## 7. 使用场景

### 场景 1：创建新模版
1. 点击"创建模板"
2. 填写基本信息
3. 在"Jenkinsfile"字段输入初始内容
4. 保存

### 场景 2：修改现有版本
1. 进入版本管理
2. 点击"编辑内容"
3. 修改 Jenkinsfile
4. 保存

### 场景 3：基于现有版本创建新版本
1. 点击"自动迭代"
2. 系统复制当前版本的所有内容（包括 Jenkinsfile）
3. 版本号自动递增
4. 可以再次编辑新版本的内容

### 场景 4：跨环境迁移
1. 在源环境导出模版（包含 Jenkinsfile）
2. 修改 JSON 中的 code 字段
3. 在目标环境导入
4. Jenkinsfile 内容完整迁移

## 8. 数据库字段

### PipelineTemplateVersion 表
- `content` (TextField)：存储完整的 Jenkinsfile 内容
- `stages_content` (JSONField)：存储各阶段的独立脚本

### 区别
- `content`：完整的 Jenkinsfile 脚本
- `stages_content`：按阶段拆分的脚本片段

## 9. 前端组件

### 编辑器
- 使用 `<a-textarea>` 组件
- 等宽字体（font-mono）
- 20 行高度
- 支持滚动

### 查看器
- 使用 `<pre>` 标签
- 只读模式
- 保留格式
- 支持滚动

## 10. 测试步骤

### 测试 1：编辑内容
1. 进入版本管理
2. 点击"编辑内容"
3. 修改 Jenkinsfile
4. 保存
5. 验证：点击"查看内容"确认修改已保存

### 测试 2：导出导入
1. 导出某个模版
2. 打开 JSON 文件，确认 content 字段有内容
3. 修改 code 字段
4. 导入
5. 验证：新模版的版本内容与原模版一致

### 测试 3：自动迭代
1. 编辑某个版本的内容
2. 点击"自动迭代"
3. 验证：新版本的 content 与原版本相同

## 11. 注意事项

- 编辑内容会更新 `update_time` 和 `modifier` 字段
- 导出始终导出最新版本的内容
- 导入时 content 字段必须存在
- 自动迭代会完整复制 content 字段

## 12. 文件清单

### 前端
- `web/apps/web-antd/src/views/release/pipelineTemplate/modules/versions.vue`
  - 添加 `handleEditContent` 函数
  - 添加 `showEditContentModal` 模态框
  - 添加"编辑内容"按钮

- `web/apps/web-antd/src/api/release/pipelineTemplate.ts`
  - 添加 `updateVersionContent` API 函数

### 后端
- `backend/release/views/pipeline_template.py`
  - `export_config` 已包含 content 字段
  - `import_config` 已支持 content 字段
  - 标准的 PUT 接口支持更新 content

- `backend/release/serializers.py`
  - `PipelineTemplateVersionSerializer` 支持 content 字段
  - `PipelineTemplateVersionCreateSerializer` 支持 content 字段

## 13. 快速启动

```bash
# 1. 重启前端
cd web
rm -rf node_modules/.vite
npm run dev:antd

# 2. 刷新浏览器
# Ctrl+Shift+R

# 3. 测试功能
# - 进入流水线模版
# - 点击版本管理
# - 看到"编辑内容"按钮
```

## 14. 常见问题

### Q: 编辑内容后看不到变化？
A: 点击"查看内容"确认是否保存成功，检查浏览器控制台是否有错误。

### Q: 导出的 JSON 中 content 为空？
A: 确认该模版有最新版本，且最新版本有 content 内容。

### Q: 导入后内容丢失？
A: 检查 JSON 文件中 version.content 字段是否存在且有值。

### Q: 编辑内容按钮点击无反应？
A: 检查浏览器控制台错误，确认 API 请求是否成功。
