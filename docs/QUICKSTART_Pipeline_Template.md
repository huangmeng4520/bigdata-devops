# Pipeline 模版管理功能快速启动指南

## 1. 数据库迁移

```bash
cd backend
python manage.py migrate release
```

## 2. 启动后端服务

```bash
cd backend
python manage.py runserver
```

## 3. 启动前端服务

```bash
cd web
npm run dev:antd
```

## 4. 访问系统

浏览器访问: http://localhost:5173

导航到: **发布管理 > 流水线模版**

## 5. 功能验证

### 5.1 创建模版
1. 点击"创建模版"
2. 填写信息:
   - 名称: Java Maven CI
   - 编码: java_maven_ci
   - 类型: CI 模版
   - 语言: Java
   - 版本号: 1.0.0
3. 点击确认

### 5.2 复制模版
1. 找到刚创建的模版
2. 点击"复制"
3. 验证生成了新模版（编码为 java_maven_ci_copy）

### 5.3 导出模版
1. 点击"导出"
2. 验证下载了 JSON 文件

### 5.4 导入模版
1. 点击"导入模版"
2. 选择刚导出的 JSON 文件
3. 修改 JSON 中的 code 字段（避免重复）
4. 验证导入成功

### 5.5 版本管理
1. 点击"版本管理"
2. 点击"自动迭代"
3. 验证生成了新版本（1.0.1）

### 5.6 编辑阶段
1. 在版本列表中点击"编辑阶段"
2. 选择一个阶段
3. 修改脚本内容
4. 保存并验证

## 6. API 测试

### 复制模版
```bash
curl -X POST http://localhost:8000/api/release/pipeline-templates/1/copy/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Java Maven CI Copy", "code": "java_maven_ci_copy2"}'
```

### 导出模版
```bash
curl http://localhost:8000/api/release/pipeline-templates/1/export_config/
```

### 自动版本迭代
```bash
curl -X POST http://localhost:8000/api/release/pipeline-template-versions/1/auto_version/ \
  -H "Content-Type: application/json" \
  -d '{"change_log": "自动迭代测试"}'
```

### 更新阶段脚本
```bash
curl -X PUT http://localhost:8000/api/release/pipeline-template-versions/1/update_stage/ \
  -H "Content-Type: application/json" \
  -d '{"stage_name": "Build", "stage_script": "sh \"mvn clean package\""}'
```

## 7. 常见问题

### Q: 迁移失败
A: 确保数据库连接正常，检查 settings.py 中的数据库配置

### Q: 导入失败提示编码已存在
A: 修改 JSON 文件中的 code 字段，确保唯一性

### Q: 自动迭代失败
A: 检查当前版本号格式是否为 x.y.z

### Q: 阶段编辑没有阶段可选
A: 确保版本的 stages 字段有定义阶段

## 8. 相关文档

- [PRD 文档](./PRD_Pipeline_Template_Management.md)
- [实现总结](./IMPLEMENTATION_SUMMARY.md)
- [项目 README](../README.md)
