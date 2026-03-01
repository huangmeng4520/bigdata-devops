## 如果这个项目让你有所收获，记得 Star 关注哦，这对我是非常不错的鼓励与支持。


# 项目简介

本项目为基于 Django5 + Vue3（vben-admin）全栈开发的企业级中后台管理系统，支持动态菜单、按钮权限、自动化代码生成、前后端权限联动等功能，适用于多角色、多权限场景的管理后台。

新增 ai_service 子项目，基于 FastAPI 实现，集成了 AI 对话能力，支持接入 DeepSeek 等大模型，实现智能对话、知识问答等功能，可灵活扩展多种 AI 场景。

## 在线体验

- admin/admin123  
- chenze/admin123

体验地址：https://demo.ywwuzi.cn

文档地址：https://docs.ywwuzi.cn

## 功能截图

<table>
 <tr>
    <td><strong>AI对话</strong><br><img src="images/ai_chat.png" alt="AI对话" width="400"></td>
    <td><strong>AI绘画</strong><br><img src="images/ai_drawing.png" alt="AI对话" width="400"></td>
  </tr>
  <tr>
    <td><strong>部门管理</strong><br><img src="images/dj_dept.png" alt="部门管理" width="400"></td>
    <td><strong>用户管理</strong><br><img src="images/dj_user.png" alt="用户管理" width="400"></td>
  </tr>
  <tr>
    <td><strong>角色管理</strong><br><img src="images/dj_role.png" alt="角色管理" width="400"></td>
    <td><strong>岗位管理</strong><br><img src="images/dj_post.png" alt="岗位管理" width="400"></td>
  </tr>
  <tr>
    <td><strong>菜单管理</strong><br><img src="images/dj_menu.png" alt="菜单管理" width="400"></td>
    <td><strong>前端界面</strong><br><img src="images/dj_vue1.png" alt="前端界面" width="400"></td>
  </tr>
  <tr>
    <td><strong>权限员工界面</strong><br><img src="images/dj_chenze.png" alt="普通员工界面" width="400"></td>
    <td></td>
  </tr>
</table>

# 许可证

本项目遵循 MIT License。
它是一个完全开源的快速开发平台，个人、团体使用免费，Django-Vue3-Admin 是一个基于 RBAC（基于角色的访问控制）模型进行权限控制的全面基础开发平台，权限控制粒度达到列级。它遵循前后端分离的架构，后端使用 Django 和 Django Rest Framework，前端使用 Vue3、Composition API、TypeScript、Vite 和 vben-admin（Ant Design Vue）。

# 启动说明
python 版本 3.12

node 版本v22.17.0
## 后端启动

0. 修改数据库配置：
   打开 backend/backend/settings.py，找到 DATABASES，根据实际情况修改数据库连接信息（如主机、端口、用户名、密码、数据库名等）。
   ```python
   DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'django_vue',
        'USER': 'root',
        'PASSWORD': '',
        'HOST': 'localhost',
    }
}
```
1. 进入 backend 目录：
   ```bash
   cd backend
   ```
2. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```
3. 导入数据库（默认 MySQL）：
   ```bash
   # 先在 MySQL 中创建数据库（如 django_vue）
   mysql -h 127.0.0.1 -u root -p -e "CREATE DATABASE IF NOT EXISTS django_vue DEFAULT CHARSET utf8mb4 COLLATE utf8mb4_unicode_ci;"
   # 导入数据
   mysql -h 127.0.0.1 -u root -p django_vue < ./sql/django_vue.sql
   ```
   sql 文件位于 sql/django_vue.sql。
   如需更换数据库类型，请修改 backend/backend/settings.py 中的数据库配置。
4. 启动服务：
   ```bash
   python manage.py runserver
   ```


## (可选)Django 项目中启动 Celery 的标准方法如下：
### Celery 任务队列与监控
### 启动 Celery Worker
![Celery 启动界面](images/celery.png)

```bash
celery -A backend worker -l info
```

### 启动 Celery Beat（如有定时任务）
定时任务配置在 `backend/backend/settings.py` 的 `CELERY_BEAT_SCHEDULE`。
```python
CELERY_BEAT_SCHEDULE = {
    'every-1-minutes': {
        'task': 'system.tasks.sync_temu_order',  # 任务路径
        'schedule': 60,  # 每1分钟执行一次
    },
}
```
```bash
celery -A backend beat -l info
```

### 启动 Flower 监控

```bash
celery -A backend flower --port=5555 --basic_auth=admin:admin123
```

- `--port=5555`：指定 Flower 的访问端口（可自定义）
- `--basic_auth=用户名:密码`：设置访问 Flower 的账号密码（如 admin:admin123）

启动后，浏览器访问 [http://localhost:5555](http://localhost:5555) ，输入账号密码即可进入 Celery 任务监控界面。

![Celery 监控界面](images/flower.png)

---

## 前端启动（以 web-antd 为例）

> 说明：web-ele 目前暂不支持，待 InputPassword 等组件开发完毕后再兼容。

1. 进入前端目录：
   ```bash
   cd web
   ```
2. 安装依赖：
   ```bash
   pnpm install
   ```
3. 启动开发服务：
   ```bash
   npm run dev:antd
   ```


# Docker 启动与部署

## 开发环境一键启动

1. 复制开发环境变量模板（如有）：
   ```bash
   cp docker/.env.example docker/.env.local
   # 根据实际情况修改 docker/.env.local
   ```
2. 构建并启动所有开发服务：
   ```bash
   docker compose -f docker-compose.dev.yml up -d --build
   ```
3. 关闭所有开发服务：
   ```bash
   docker compose -f docker-compose.dev.yml down
   ```

> 如需自定义端口、数据库、Redis 密码等，请修改 `docker/.env.local` 文件。

## 生产环境一键启动

本项目支持一键 Docker 部署，推荐生产环境使用。

1. 复制环境变量模板：
   ```bash
   cp docker/.env.example docker/.env.local
   # 根据实际情况修改 docker/.env.local
   ```
2. 构建并启动所有服务：
   ```bash
   docker compose -f docker-compose.prod.yml up -d --build
   ```
3. 关闭所有服务：
   ```bash
   docker compose -f docker-compose.prod.yml down
   ```

如需自定义端口、数据库、Redis 密码等，请修改 docker/.env.local 文件。

## 阿里云 OSS 配置

### 启用 OSS 上传

1. 在 `docker/.env.prod` 中配置 OSS 参数：
   ```env
   VITE_OSS_ENABLED=true
   VITE_OSS_REGION=oss-cn-hangzhou
   VITE_OSS_ACCESS_KEY_ID=your_access_key_id
   VITE_OSS_ACCESS_KEY_SECRET=your_access_key_secret
   VITE_OSS_BUCKET=your_bucket_name
   VITE_OSS_PREFIX=frontend/
   VITE_OSS_DELETE_LOCAL=false
   ```

### 禁用 OSS 上传

将 `VITE_OSS_ENABLED` 设置为 `false` 或删除相关配置即可。

## 演示环境配置

### 启用演示模式

在 `docker/.env.prod` 中设置：

```env
DEMO_MODE=true
```

演示模式下：
- 全局禁止所有修改和删除操作（POST、PUT、PATCH、DELETE）
- 只允许登录、登出等基础操作
- 所有修改/删除请求将返回 403 错误
- **禁用 Django Admin 后台管理界面**
- 适用于在线演示，防止数据被误操作

### 禁用演示模式

将 `DEMO_MODE` 设置为 `false` 或删除该配置即可正常使用所有功能，包括 Admin 后台。

---

# 技术架构

- **后端**：Django + Django REST framework
- **前端**：Vue3 + Vite + vben-admin（Ant Design Vue）
- **数据库**：默认 MySQL，可扩展为 PostgreSQL

# 后端技术栈

- Python 3.12+
- Django 5.x
- Django REST framework
- Celery（可选，任务队列）
- 角色/菜单/按钮权限模型
- 自动化菜单/权限生成脚本

# 前端技术栈

- Vue3
- Vite
- TypeScript
- Pinia（状态管理）
- Ant Design Vue
- vben-admin 组件库
- 动态路由与权限指令

# 功能特点

- 动态菜单与多级路由，支持后端驱动
- 按钮级别权限控制，支持 v-permission 指令
- 角色多对多、权限灵活分配
- 自动化脚本生成菜单与权限
- 通用权限校验，支持接口级、按钮级
- 登录日志、操作日志
- 支持多端适配与主题切换
- 代码生成器辅助开发

# mysql-client 安装报错

```angular2html
 brew install mysql-client  
If you need to have mysql-client first in your PATH, run:
  echo 'export PATH="/opt/homebrew/opt/mysql-client/bin:$PATH"' >> ~/.zshrc

For compilers to find mysql-client you may need to set:
  export LDFLAGS="-L/opt/homebrew/opt/mysql-client/lib"
  export CPPFLAGS="-I/opt/homebrew/opt/mysql-client/include"

For pkgconf to find mysql-client you may need to set:
  export PKG_CONFIG_PATH="/opt/homebrew/opt/mysql-client/lib/pkgconfig"

```

cd backend
python manage.py runserver
celery -A backend worker -l info


目前系统已经完成基本骨架，需要继续探索关于ci、cd 针对不同语言下面的模版，已经支持针对不用应用在不同stage的自定义，模版支持版本管理、应用的ci、cd支持版本管理。在测试环境时，cicd可以合并到一个流水线完成，针对准生产和生产环境，ci和cd需要分离，ci在互联网的jenkins，cd在政务网的jenkins，由于互联网和政务网是无法直接通信的，互联网jenkins的ci可以直接创建，针对政务网的cd，生产保存到系统可以下载配置文件及复制配置。针对此需求需要出详细的prd并存到醒目工程下

### 4.1 标准化命名规范
按照项目、模块、应用、环境的维度，对资源进行标准化命名。project和medicare不能有“-”字符。
| 资源类型 | 命名格式 | 示例 |
|----------|----------|------|
| GitLab Group | `<project>` | `medicare` |
| GitLab Subgroup | `<module>` | `payment` |
| GitLab Repository | `<app>` | `service` |
| 互联网Harbor项目 | `<project>-<module>` | `medicare-payment` |
| 镜像名 | `<app>` | `service` |
| 镜像标签 | `<version>-<environment>` | `1.2.3-uat` |
| 政务网Jenkins任务 | `<project>/<module>/<app>/<env>` | `medicare/payment/service/uat` |
| Ansible Inventory | `inventory/<project>/<module>/<app>/<env>` | `inventory/medicare/payment/service/uat` 



我在梳理下逻辑，1、流水线模版是保存常见的语言cicd的jenkinsfile脚本，需要支持新增、修改、查看。修改保存时自动版本迭代。2、当创建应用时可以关联到流水线模版到cicd，保存应用时把cicd模版传递给jenkins，同时应用支持改变cicd并同步到Jenkins。 

jenkins pipeline 模版管理的需求
- 支持不同语言的流水线模版
- 自动版本迭代
- 关联应用时可传递模版到Jenkins
- 支持应用变更模版并同步
- 支持模版的版本管理
- 支持模版的复制
- 支持模版的导入
- 支持模版的导出
- 针对pipeline每个阶段的脚本独立修改


问题1：创建新版本优化
✅ 点击"创建新版本"时，自动生成下一个版本号（自动递增）
✅ 版本号格式：基于最新版本号，递增最后一个数字（如 1.0.0 → 1.0.1）
✅ 扩大了 Jenkinsfile 编辑框为 18 行
✅ 表单布局优化，使用 Row/Col 栅格布局
问题2：编辑 Stage 自动创建新版本
✅ 保存 Stage 编辑后，自动创建新版本而不是修改原版本
✅ 新版本号自动递增
✅ 变更日志自动记录：编辑 Stage: xxx
✅ 添加了提示信息："保存后将自动创建新版本（版本号自动递增），不会修改原版本"
✅ 弹窗标题显示基于哪个版本编辑

http://localhost:8083/git_add_group/sugroup_moudel/owner-05.git



pipeline {
    agent any
    parameters {
        string(name: 'PROJECT', defaultValue: 'git_add_group', description: '项目名称')
        string(name: 'MODULE', defaultValue: 'sugroup_moudel', description: '模块名称')
        string(name: 'APP', defaultValue: 'owner-05', description: '应用名称')
        string(name: 'BRANCH', defaultValue: 'main', description: '代码分支')
        string(name: 'VERSION', defaultValue: '', description: '版本号（可选）')
    }
    environment {
        DOCKER_REGISTRY = 'https://192.168.3.134/'
        GIT_REPO = "http://192.168.3.134:8083/${params.PROJECT}/${params.MODULE}/${params.APP}.git"
        // 镜像全名：harbor.internet.com/medicare-payment/service:标签
        IMAGE_BASE = "${DOCKER_REGISTRY}/${params.PROJECT}-${params.MODULE}/${params.APP}"
    }
    stages {
        stage('Checkout') {
            steps {
                git branch: params.BRANCH, url: GIT_REPO,
            credentialsId: 'gitlab-http-credentials'   // 你设置的 ID
            }
        }
        stage('Determine Version and Tag') {
            steps {
                script {
                    // 如果未传入 VERSION，从文件读取（仅主干或发布分支）
                    if (!params.VERSION) {
                        if (params.BRANCH == 'main' || params.BRANCH.startsWith('release/')) {
                            def versionFile = readFile('VERSION').trim()
                            currentBuild.displayName = "${versionFile}"
                            env.VERSION = versionFile
                        } else {
                            env.VERSION = "test-${env.BUILD_ID}"
                        }
                    } else {
                        env.VERSION = params.VERSION
                    }
                    
                    // 根据分支确定镜像标签后缀
                    if (params.BRANCH == 'develop' || params.BRANCH.startsWith('feature/')) {
                        env.TAG_SUFFIX = 'test'
                    } else if (params.BRANCH == 'main' || params.BRANCH.startsWith('release/')) {
                        env.TAG_SUFFIX = 'uat'
                    } else if (params.BRANCH.startsWith('hotfix/')) {
                        env.TAG_SUFFIX = 'uat'   // 热修复先发布到UAT验证
                    } else {
                        env.TAG_SUFFIX = 'test'
                    }
                    
                    env.FULL_TAG = "${env.VERSION}-${env.TAG_SUFFIX}"
                    env.IMAGE = "${IMAGE_BASE}:${env.FULL_TAG}"
                }
            }
        }
        stage('Build & Test') {
            steps {
                <!-- sh 'mvn clean package'   // 示例，可根据实际语言调整 -->
                sh 'mvn clean package'   // 示例，可根据实际语言调整
            }
        }
        stage('Docker Build') {
            steps {
                sh "docker build -t ${IMAGE} ."
            }
        }
                stage('Push to Harbor') {
            steps {
                withCredentials([usernamePassword(
                    credentialsId:'7733a704-bda5-4bf1-a5d9-d5bc26e940e1', // 替换成你第一步中设置的ID
                    passwordVariable: 'HARBOR_PASS', 
                    usernameVariable: 'HARBOR_USER'
                )]) {
                    sh """
                        # 使用从凭据注入的用户名和密码登录
                        docker login ${DOCKER_REGISTRY} -u ${HARBOR_USER} -p ${HARBOR_PASS}
                        docker push ${IMAGE}
                        # 可选：登出，清理本地凭证
                        docker logout ${DOCKER_REGISTRY}
                    """
                }
            }
        }
    }
}


在应用上面怎么加发布按钮、发布多模态框支持选择不同的分支、支持选择不同的环境、支持选择审批，并自定义审批人，确定后弹出发布信息确认框，确认后触发jenkins的job构建。发布记录需要记录在当前系统以便审计，Jenkins job的构建日志需要记录在本系统，先出简版的prd文档，核心是把逻辑关系理清楚，包括前端和后端的实现


发布需要考虑是否有sql执行，可以规定固定存放目录，在发布是记录到发布日志，方便回滚是dba进行处理。