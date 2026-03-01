# 前端按钮不显示问题排查指南

## 问题描述
模版的分阶段编辑、复制、导出、查看等操作按钮在前端看不到。

## 排查步骤

### 1. 确认代码已正确添加 ✅
运行验证脚本确认：
```bash
./verify_frontend.sh
```

所有功能代码已正确添加到文件中。

### 2. 重启前端服务

**停止当前服务**（如果正在运行）：
- 按 `Ctrl + C` 停止

**清理并重启**：
```bash
cd web
rm -rf node_modules/.vite  # 清除 Vite 缓存
npm run dev:antd
```

### 3. 清除浏览器缓存

**Chrome/Edge**：
1. 打开开发者工具（F12）
2. 右键点击刷新按钮
3. 选择"清空缓存并硬性重新加载"

**或者**：
- `Ctrl + Shift + Delete` 打开清除缓存对话框
- 选择"缓存的图片和文件"
- 点击"清除数据"

### 4. 检查浏览器控制台

打开浏览器开发者工具（F12），查看：

**Console 标签**：
- 是否有 JavaScript 错误？
- 是否有 API 请求失败？
- 是否有组件加载错误？

**Network 标签**：
- 检查 `pipelineTemplate.ts` 是否正确加载
- 检查 `index.vue` 和 `versions.vue` 是否正确加载

### 5. 检查具体位置

#### 5.1 模版列表页面的操作按钮

**位置**：流水线模版列表 → 每行最右侧的"操作"列

**应该看到的按钮**：
- 编辑
- 版本管理
- **复制** ← 新增
- **导出** ← 新增
- 删除

**如果看不到**：
1. 检查表格是否正常显示
2. 检查"操作"列是否存在
3. 打开控制台查看是否有错误

#### 5.2 工具栏的导入按钮

**位置**：流水线模版列表 → 顶部工具栏

**应该看到**：
- "创建模板"按钮（蓝色）
- **"导入模板"按钮** ← 新增

#### 5.3 版本管理弹窗的操作按钮

**位置**：点击某个模版的"版本管理" → 版本列表 → 每行的"操作"列

**应该看到的按钮**：
- 设为最新（仅非最新版本显示）
- **自动迭代** ← 新增
- **编辑阶段** ← 新增
- 查看内容

### 6. 手动验证代码

#### 6.1 检查 index.vue
```bash
grep -A 5 "code: 'copy'" web/apps/web-antd/src/views/release/pipelineTemplate/index.vue
```

应该输出：
```javascript
    {
      code: 'copy',
      text: '复制',
    },
```

#### 6.2 检查 versions.vue
```bash
grep "handleAutoVersion\|handleEditStage" web/apps/web-antd/src/views/release/pipelineTemplate/modules/versions.vue
```

应该输出包含这两个函数的定义和调用。

### 7. 检查 API 导入

```bash
grep "import.*copyTemplate\|import.*exportTemplate\|import.*importTemplate" web/apps/web-antd/src/views/release/pipelineTemplate/index.vue
```

应该输出：
```javascript
import {
  copyTemplate,
  deleteTemplate,
  exportTemplate,
  getTemplateList,
  importTemplate,
} from '#/api/release';
```

### 8. 强制重新编译

如果以上都正常但仍看不到按钮：

```bash
cd web
# 停止服务
# 删除缓存
rm -rf node_modules/.vite
rm -rf dist
rm -rf apps/web-antd/.vite
# 重新安装依赖（可选）
pnpm install
# 重新启动
npm run dev:antd
```

### 9. 检查路由和权限

确认你访问的是正确的页面：
- URL 应该包含 `/release/pipeline-template` 或类似路径
- 确认当前用户有访问权限

### 10. 临时调试方法

在 `index.vue` 的 `getActionButtons` 函数中添加 console.log：

```javascript
function getActionButtons(row: PipelineTemplateApi.Template) {
  const buttons = [
    { code: 'edit', text: '编辑' },
    { code: 'versions', text: '版本管理' },
    { code: 'copy', text: '复制' },
    { code: 'export', text: '导出' },
    { code: 'delete', text: '删除', danger: true },
  ];
  console.log('Action buttons:', buttons);  // 添加这行
  return buttons;
}
```

刷新页面，打开控制台，应该能看到按钮列表输出。

## 常见问题

### Q1: 按钮代码已添加但页面没变化
**A**: 前端服务没有重启或浏览器缓存未清除。

### Q2: 控制台报错 "Cannot find module"
**A**: API 函数导入路径错误或函数未导出。检查 `pipelineTemplate.ts` 中的 export。

### Q3: 点击按钮没反应
**A**: 事件处理函数未正确绑定。检查 `onActionClick` 函数中的 switch case。

### Q4: 版本管理弹窗中看不到新按钮
**A**: 
1. 检查 `versions.vue` 是否正确保存
2. 检查是否有语法错误
3. 重启前端服务

## 快速验证命令

```bash
# 1. 验证代码
./verify_frontend.sh

# 2. 重启服务
cd web
rm -rf node_modules/.vite
npm run dev:antd

# 3. 在浏览器中
# - 清除缓存（Ctrl+Shift+Delete）
# - 硬刷新（Ctrl+Shift+R）
# - 打开控制台（F12）查看错误
```

## 预期效果截图位置

1. **模版列表页面**：
   - 工具栏应有"导入模板"按钮
   - 每行操作列应有5个按钮（编辑、版本管理、复制、导出、删除）

2. **版本管理弹窗**：
   - 版本列表每行应有3-4个按钮（设为最新、自动迭代、编辑阶段、查看内容）

## 如果问题仍未解决

请提供以下信息：
1. 浏览器控制台的完整错误信息
2. Network 标签中失败的请求
3. 当前访问的 URL
4. 前端服务启动时的输出信息
