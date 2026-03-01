# 流水线模版功能完整测试

## 功能概述

✅ **已实现的核心功能**：
1. 创建模版时自动显示初始版本和 Jenkinsfile
2. 根据选择的语言和类型自动加载默认模版
3. 支持 5 种语言的 CI 模版 + 通用 CD 模版
4. 完整的版本管理功能
5. 模版复制、导出、导入功能

## 1. 创建模版 - 自动加载默认模版

### 测试步骤

1. **点击"创建模板"按钮**

2. **填写基本信息**：
   - 模板名称：Test Java CI
   - 模板编码：test-java-ci
   - 模板类型：CI 模版
   - 编程语言：Java

3. **查看自动加载的内容**：
   - ✅ 版本号：1.0.0（自动填充）
   - ✅ Jenkinsfile：显示 Java CI 默认模版
   - ✅ 变更日志：初始版本（自动填充）
   - ✅ 设为最新版本：已勾选

4. **切换语言测试**：
   - 选择 Node.js → Jenkinsfile 自动切换为 Node.js 模版
   - 选择 Python → Jenkinsfile 自动切换为 Python 模版
   - 选择 Go → Jenkinsfile 自动切换为 Go 模版
   - 选择 .NET → Jenkinsfile 自动切换为 .NET 模版

5. **切换类型测试**：
   - 选择 CD 模版 → Jenkinsfile 自动切换为 CD 模版

6. **点击确定创建**

### 预期结果
- ✅ 模版创建成功
- ✅ 初始版本 1.0.0 自动创建
- ✅ Jenkinsfile 内容已保存
- ✅ 列表中显示新模版

## 2. 支持的默认模版

### 2.1 Java CI 模版
```groovy
pipeline {
    agent {
        kubernetes {
            label 'maven-builder'
            defaultContainer 'maven'
        }
    }
    environment {
        MAVEN_OPTS = '-Dmaven.repo.local=/root/.m2/repository'
    }
    stages {
        stage('Checkout') { ... }
        stage('Build') { ... }
        stage('Test') { ... }
        stage('Build Image') { ... }
    }
}
```

### 2.2 Node.js CI 模版
```groovy
pipeline {
    agent {
        kubernetes {
            label 'node-builder'
            defaultContainer 'node'
        }
    }
    stages {
        stage('Checkout') { ... }
        stage('Install') { ... }
        stage('Build') { ... }
        stage('Test') { ... }
        stage('Build Image') { ... }
    }
}
```

### 2.3 Python CI 模版
```groovy
pipeline {
    agent {
        kubernetes {
            label 'python-builder'
            defaultContainer 'python'
        }
    }
    stages {
        stage('Checkout') { ... }
        stage('Install') { ... }
        stage('Test') { ... }
        stage('Build Image') { ... }
    }
}
```

### 2.4 Go CI 模版
```groovy
pipeline {
    agent {
        kubernetes {
            label 'go-builder'
            defaultContainer 'golang'
        }
    }
    stages {
        stage('Checkout') { ... }
        stage('Build') { ... }
        stage('Test') { ... }
        stage('Build Image') { ... }
    }
}
```

### 2.5 .NET CI 模版
```groovy
pipeline {
    agent {
        kubernetes {
            label 'dotnet-builder'
            defaultContainer 'dotnet'
        }
    }
    stages {
        stage('Checkout') { ... }
        stage('Build') { ... }
        stage('Test') { ... }
        stage('Build Image') { ... }
    }
}
```

### 2.6 CD 模版（通用）
```groovy
pipeline {
    agent {
        kubernetes {
            label 'deployer'
        }
    }
    parameters {
        choice(name: 'ENV', choices: ['dev', 'test', 'staging', 'production'], description: '部署环境')
        string(name: 'IMAGE_TAG', description: '镜像标签')
    }
    stages {
        stage('Deploy') { ... }
        stage('Health Check') { ... }
    }
}
```

## 3. 编辑模版

### 测试步骤
1. 点击某个模版的"编辑"按钮
2. 查看表单内容

### 预期结果
- ✅ 只显示模版基本信息
- ✅ 不显示版本号字段
- ✅ 不显示 Jenkinsfile 字段
- ✅ 模版编码不可编辑
- ✅ 可以修改名称、类型、语言等

## 4. 版本管理

### 4.1 查看版本列表
1. 点击"版本管理"按钮
2. 查看版本列表

**预期结果**：
- ✅ 显示所有版本
- ✅ 最新版本有绿色标记
- ✅ 显示版本号、状态、变更日志、创建时间

### 4.2 创建新版本
1. 点击"创建新版本"
2. 输入版本号：1.1.0
3. 输入 Jenkinsfile 内容
4. 点击"从最新版本复制"可复制内容
5. 点击创建

**预期结果**：
- ✅ 新版本创建成功
- ✅ 版本列表中显示新版本

### 4.3 编辑内容
1. 点击某个版本的"编辑内容"
2. 修改 Jenkinsfile
3. 点击确定

**预期结果**：
- ✅ 内容更新成功
- ✅ 点击"查看内容"可验证

### 4.4 自动迭代
1. 点击某个版本的"自动迭代"
2. 确认对话框

**预期结果**：
- ✅ 版本号自动递增（1.0.0 → 1.0.1）
- ✅ 内容自动复制
- ✅ 自动设为最新版本

### 4.5 编辑阶段
1. 点击"编辑阶段"
2. 选择阶段（如 Build）
3. 修改脚本
4. 点击确定

**预期结果**：
- ✅ 阶段脚本更新成功

### 4.6 查看内容
1. 点击"查看内容"

**预期结果**：
- ✅ 只读模式显示完整 Jenkinsfile
- ✅ 保留格式

## 5. 模版操作

### 5.1 复制模版
1. 点击"复制"按钮

**预期结果**：
- ✅ 生成新模版（编码 + _copy）
- ✅ 版本号重置为 1.0.0
- ✅ 内容完整复制

### 5.2 导出模版
1. 点击"导出"按钮

**预期结果**：
- ✅ 下载 JSON 文件
- ✅ 文件名：{编码}_template.json
- ✅ 包含完整 Jenkinsfile 内容

### 5.3 导入模版
1. 点击"导入模板"
2. 选择 JSON 文件

**预期结果**：
- ✅ 模版导入成功
- ✅ Jenkinsfile 内容完整

### 5.4 删除模版
1. 点击"删除"
2. 确认对话框

**预期结果**：
- ✅ 模版删除成功
- ✅ 从列表中消失

## 6. 搜索和筛选

### 测试步骤
1. 选择模版类型：CI
2. 选择语言：Java
3. 输入名称搜索

**预期结果**：
- ✅ 显示匹配的模版
- ✅ 实时筛选

## 7. 完整测试流程

### 流程 1：创建 Java CI 模版
```
1. 点击"创建模板"
2. 名称：Java Maven CI
3. 编码：java-maven-ci
4. 类型：CI
5. 语言：Java
6. 查看自动加载的 Jenkinsfile（Maven 构建）
7. 点击确定
✓ 验证：模版和版本 1.0.0 创建成功
```

### 流程 2：切换语言测试
```
1. 点击"创建模板"
2. 选择语言：Node.js
3. 查看 Jenkinsfile 自动切换为 npm 构建
4. 选择语言：Python
5. 查看 Jenkinsfile 自动切换为 pip 构建
✓ 验证：Jenkinsfile 根据语言自动切换
```

### 流程 3：版本管理
```
1. 点击模版的"版本管理"
2. 点击"创建新版本"，输入 1.1.0
3. 点击"从最新版本复制"
4. 修改内容，点击创建
5. 点击版本 1.1.0 的"自动迭代"
✓ 验证：生成版本 1.1.1
```

### 流程 4：编辑内容
```
1. 进入版本管理
2. 点击"编辑内容"
3. 修改 Jenkinsfile（如添加注释）
4. 点击确定
5. 点击"查看内容"验证
✓ 验证：内容已更新
```

### 流程 5：复制和导入导出
```
1. 点击"复制"
✓ 验证：生成 {编码}_copy 模版

2. 点击"导出"
✓ 验证：下载 JSON 文件，包含 Jenkinsfile

3. 修改 JSON 中的 code
4. 点击"导入模板"
✓ 验证：导入成功，Jenkinsfile 完整
```

## 8. 功能清单

### ✅ 已实现
- [x] 创建模版显示初始版本和 Jenkinsfile
- [x] 根据语言自动加载默认模版
- [x] 支持 5 种语言 CI 模版
- [x] 支持通用 CD 模版
- [x] 切换语言/类型自动更新 Jenkinsfile
- [x] 编辑模版不显示版本字段
- [x] 版本管理（创建、编辑、查看、迭代）
- [x] 编辑 Jenkinsfile 内容
- [x] 编辑阶段脚本
- [x] 自动版本迭代
- [x] 复制模版
- [x] 导出模版（包含 Jenkinsfile）
- [x] 导入模版（包含 Jenkinsfile）
- [x] 搜索和筛选
- [x] 删除模版

### 🎯 核心特性
1. **智能默认模版**：根据语言和类型自动加载
2. **实时切换**：切换语言时 Jenkinsfile 自动更新
3. **版本管理**：完整的版本生命周期管理
4. **内容编辑**：支持完整编辑和阶段独立编辑
5. **导入导出**：支持跨环境迁移

## 9. 注意事项

1. **创建模版**：必须填写初始版本的 Jenkinsfile
2. **编辑模版**：只能编辑基本信息，不能编辑 Jenkinsfile
3. **编辑 Jenkinsfile**：通过"版本管理" → "编辑内容"
4. **版本号格式**：建议使用语义化版本（x.y.z）
5. **模版编码**：创建后不可修改

## 10. 快速验证命令

```bash
# 重启服务
cd web && npm run dev:antd
cd backend && python manage.py runserver

# 测试步骤
1. 打开浏览器：http://localhost:5678/release/pipeline-template
2. 点击"创建模板"
3. 选择不同语言，观察 Jenkinsfile 变化
4. 创建模版
5. 进入版本管理测试各项功能
```

## 11. 已修复的问题

- ✅ 修复编辑时显示版本字段问题
- ✅ 修复创建版本缺少 template 字段
- ✅ 修复编辑时编码唯一性验证
- ✅ 修复版本列表渲染错误
- ✅ 修复 Modal 数据传递问题
- ✅ 添加语言切换自动更新 Jenkinsfile

## 12. 测试通过标准

- [ ] 创建模版时显示 Jenkinsfile
- [ ] 切换语言时 Jenkinsfile 自动更新
- [ ] 支持 5 种语言的默认模版
- [ ] 编辑模版不显示版本字段
- [ ] 版本管理功能正常
- [ ] 编辑内容功能正常
- [ ] 自动迭代功能正常
- [ ] 复制、导出、导入功能正常
- [ ] 搜索筛选功能正常
