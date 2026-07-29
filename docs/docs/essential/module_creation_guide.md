---
sidebar_position: 10
---

# 新建模块

本文档适用于本项目（Django + Vue3），指导如何规范地新建一个完整的功能模块（含后端与前端）。

---

## 一、后端模块新建流程（Django）

1. **新建Django App**
   ```bash
   cd backend
   python manage.py startapp <模块名>
   # 如： python manage.py startapp ai
   ```
   > 建议模块名使用小写英文，避免与已有模块重名。

2. **注册App**
   - 在 `backend/backend/settings.py` 的 `INSTALLED_APPS` 中添加新模块。
   ```python
   INSTALLED_APPS = [
    "simpleui",
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    "rest_framework",
    'django_filters',
    'corsheaders',
    'rest_framework.authtoken',
    "system",
    "ai",  # 新加
   ]
   ```

3. **定义模型（models.py）**
   - 继承 `CoreModel`，包含必要的审计字段（如 creator、modifier）。
   - 示例：
   ```python
   from system.models import CoreModel
   class AIApiKey(CoreModel):
      """ AI API 密钥表 """
      name = models.CharField(max_length=255, db_comment="名称")
      platform = models.CharField(max_length=255, db_comment="平台")
   ```

4. **生成迁移并迁移数据库**
   ```bash
   python manage.py makemigrations <模块名>
   python manage.py migrate
   ```

5. **注册路由（urls.py）**
   - 按照RESTful规范注册路由。 在ai文件夹下新建urls文件，并添加以下内容
   ```python
   from django.urls import include, path
   from rest_framework import routers

   from . import views

   router = routers.DefaultRouter()

   urlpatterns = [
      path('', include(router.urls)),

   ]
   ```
6. **修改路由（urls.py）**
   - 按照RESTful规范注册路由。 在ai文件夹下新建urls文件，并添加以下内容
   ```python
   urlpatterns = [
      path('api/system/', include('system.urls')),
      path('api/ai/', include('ai.urls')),  # 新加
   ]
   ```

7. **权限与菜单自动生成（推荐）**
   - 使用代码生成器：
     ```bash
     python manage.py generate_crud <模块名> <模型名> --frontend
     ```

8. ** 
```python
# 在ai/views下新建   __init__.py文件
__all__ = [
   'AIApiKeyViewSet'
]

from ai.views.ai_api_key import AIApiKeyViewSet
```


---

## 二、前端模块新建流程（Vue3）（代码生成器已经生成）
1. **配置多语言**
   在web/apps/web-antd/src/locales/langs/zh-CN/ai.json 配置多语言
   ```json
   {
      "title": "AI 大模型"
   }

   ```

2. **新建菜单配置**

   ![new_module](./new_module.png)


3. **生成权限菜单**
```shell
   cd backend
   python manage.py gen_menu_json --app ai --model AIApiKey --parent AI
```



---

## 三、注意事项

- 模块命名规范统一，避免重复。
- 建议优先使用代码生成器自动生成基础代码，减少重复劳动。
- 新模块需补充单元测试和接口文档。
- 前后端接口字段需保持一致，类型安全。
- 权限点、菜单、路由需同步配置。
- 按钮权限码必须遵循《[权限码命名规范](./permission_code_convention.md)》，`model_name` 段使用下划线（如 `code_repository`、`release_record`），禁止连字符或简写；提交前可运行 `python manage.py check_permission_codes` 自检。
- 代码提交前请自查并走团队代码评审流程。

---

如有疑问请联系项目负责人或查阅项目主文档。 