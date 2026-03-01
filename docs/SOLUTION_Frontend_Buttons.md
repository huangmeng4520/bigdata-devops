# 前端按钮不显示问题 - 解决方案

## 问题确认

✅ **代码已正确添加**，验证结果：
- 复制按钮代码：已添加
- 导出按钮代码：已添加  
- 导入按钮代码：已添加
- 自动迭代代码：已添加
- 编辑阶段代码：已添加

## 原因分析

前端按钮看不到的常见原因：
1. **前端服务未重启** - Vite 热更新可能未生效
2. **浏览器缓存** - 旧的 JS 文件仍在使用
3. **编译缓存** - Vite 缓存了旧版本

## 解决步骤

### 步骤 1: 停止前端服务
在运行前端的终端按 `Ctrl + C`

### 步骤 2: 清除 Vite 缓存
```bash
cd web
rm -rf node_modules/.vite
rm -rf apps/web-antd/.vite
```

### 步骤 3: 重启前端服务
```bash
npm run dev:antd
```

### 步骤 4: 清除浏览器缓存
**方法 1（推荐）**：
1. 打开开发者工具（F12）
2. 右键点击浏览器刷新按钮
3. 选择"清空缓存并硬性重新加载"

**方法 2**：
1. 按 `Ctrl + Shift + Delete`
2. 选择"缓存的图片和文件"
3. 点击"清除数据"
4. 按 `Ctrl + Shift + R` 硬刷新页面

### 步骤 5: 验证功能

#### 5.1 模版列表页面
导航到：**发布管理 > 流水线模版**

**工具栏应该看到**：
- [创建模板] 按钮（蓝色）
- [导入模板] 按钮 ← **新增**

**每行操作列应该看到**：
- 编辑
- 版本管理
- 复制 ← **新增**
- 导出 ← **新增**
- 删除（红色）

#### 5.2 版本管理弹窗
点击任意模版的"版本管理"按钮

**版本列表每行操作列应该看到**：
- 设为最新（仅非最新版本显示）
- 自动迭代 ← **新增**
- 编辑阶段 ← **新增**
- 查看内容

## 如果仍然看不到

### 检查 1: 浏览器控制台
按 F12 打开开发者工具，查看 Console 标签：
- 是否有红色错误？
- 是否有 404 错误？
- 是否有语法错误？

### 检查 2: Network 标签
1. 打开 Network 标签
2. 刷新页面
3. 搜索 `pipelineTemplate`
4. 检查相关文件是否正确加载

### 检查 3: 手动验证代码
```bash
# 验证操作按钮
grep "code: 'copy'" web/apps/web-antd/src/views/release/pipelineTemplate/index.vue

# 验证导入按钮
grep "导入模板" web/apps/web-antd/src/views/release/pipelineTemplate/index.vue

# 验证版本管理按钮
grep "handleAutoVersion\|handleEditStage" web/apps/web-antd/src/views/release/pipelineTemplate/modules/versions.vue
```

所有命令都应该有输出。

### 检查 4: 完全重新编译
```bash
cd web
# 停止服务
rm -rf node_modules/.vite
rm -rf dist
rm -rf apps/web-antd/.vite
pnpm install  # 重新安装依赖
npm run dev:antd
```

## 功能测试

### 测试 1: 复制模版
1. 在模版列表找到任意模版
2. 点击"复制"按钮
3. 应该提示"正在复制..."
4. 成功后列表中出现新模版（编码带 _copy 后缀）

### 测试 2: 导出模版
1. 点击任意模版的"导出"按钮
2. 应该自动下载 JSON 文件
3. 文件名格式：`{模版编码}_template.json`

### 测试 3: 导入模版
1. 点击工具栏的"导入模板"按钮
2. 选择之前导出的 JSON 文件
3. 修改 JSON 中的 `code` 字段（避免重复）
4. 应该提示导入成功

### 测试 4: 自动版本迭代
1. 点击某个模版的"版本管理"
2. 在版本列表中点击"自动迭代"
3. 确认对话框
4. 应该创建新版本，版本号自动递增（如 1.0.0 → 1.0.1）

### 测试 5: 编辑阶段
1. 在版本管理中点击"编辑阶段"
2. 选择一个阶段（如 Build）
3. 修改脚本内容
4. 点击确定
5. 应该提示"阶段脚本更新成功"

## 预期效果对比

### 修改前
**模版列表操作列**：
- 编辑
- 版本管理
- 删除

**版本管理操作列**：
- 设为最新
- 查看内容

### 修改后
**模版列表操作列**：
- 编辑
- 版本管理
- **复制** ← 新增
- **导出** ← 新增
- 删除

**模版列表工具栏**：
- 创建模板
- **导入模板** ← 新增

**版本管理操作列**：
- 设为最新
- **自动迭代** ← 新增
- **编辑阶段** ← 新增
- 查看内容

## 常见错误及解决

### 错误 1: "Cannot find module '#/api/release'"
**原因**：路径别名配置问题
**解决**：检查 `vite.config.ts` 中的 alias 配置

### 错误 2: "copyTemplate is not a function"
**原因**：API 函数未正确导出
**解决**：检查 `pipelineTemplate.ts` 中的 export 语句

### 错误 3: 点击按钮无反应
**原因**：事件处理函数未绑定
**解决**：检查 `onActionClick` 函数中的 switch case

### 错误 4: 按钮显示但点击报 404
**原因**：后端 API 未启动或路由未配置
**解决**：
1. 确认后端服务正在运行
2. 执行数据库迁移：`python manage.py migrate release`
3. 检查后端路由配置

## 快速命令汇总

```bash
# 1. 清除缓存并重启前端
cd web
rm -rf node_modules/.vite
npm run dev:antd

# 2. 验证代码
cd ..
./verify_frontend.sh

# 3. 执行数据库迁移（如果还没执行）
cd backend
python manage.py migrate release

# 4. 启动后端服务
python manage.py runserver
```

## 联系支持

如果按照以上步骤仍无法解决，请提供：
1. 浏览器控制台的完整错误截图
2. Network 标签中的请求列表截图
3. 前端服务启动时的输出日志
4. 当前访问的完整 URL

## 相关文档

- [功能实现总结](./IMPLEMENTATION_SUMMARY.md)
- [快速启动指南](./QUICKSTART_Pipeline_Template.md)
- [PRD 文档](./PRD_Pipeline_Template_Management.md)
