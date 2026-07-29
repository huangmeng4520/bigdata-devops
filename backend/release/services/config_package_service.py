# -*- coding: utf-8 -*-
"""
配置包生成服务
生成应用配置包并上传到文件服务器
"""
import os
import json
import hashlib
import zipfile
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from django.conf import settings
from django.core.files.storage import default_storage

from .base import BaseService, ConfigService, DevOpsException


class ConfigPackageService(BaseService):
    """配置包生成服务"""

    service_name = "config_package"

    def __init__(self):
        super().__init__()
        self._init_config()

    def _init_config(self):
        """初始化配置"""
        self.storage_path = ConfigService.get(ConfigService.CONFIG_PACKAGE_PATH, "/tmp/config_packages")
        # 确保存储目录存在
        if not os.path.isabs(self.storage_path):
            self.storage_path = os.path.join(settings.BASE_DIR, self.storage_path)
        os.makedirs(self.storage_path, exist_ok=True)

    def generate_package(
        self,
        app_id: int,
        version: str = None,
        include_templates: bool = True
    ) -> Dict[str, Any]:
        """
        生成配置包

        Args:
            app_id: 应用 ID
            version: 版本号，默认使用时间戳
            include_templates: 是否包含模板文件

        Returns:
            配置包信息
        """
        from ..models import Application

        try:
            app = Application.objects.select_related("project", "module").get(pk=app_id)
        except Application.DoesNotExist:
            self._handle_error(f"应用不存在: {app_id}")

        # 生成版本号
        if not version:
            version = datetime.now().strftime("%Y%m%d%H%M%S")

        # 构建配置数据
        config_data = self._build_config_data(app)

        # 生成文件名
        filename = f"{app.project.code}_{app.module.code}_{app.code}_v{version}.zip"
        filepath = os.path.join(self.storage_path, filename)

        # 创建临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            # 写入配置文件
            config_file = os.path.join(temp_dir, "config.json")
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)

            files_to_zip = [config_file]

            # 添加模板文件
            if include_templates:
                template_files = self._get_template_files(app.app_type, temp_dir)
                files_to_zip.extend(template_files)

            # 创建 README
            readme_file = os.path.join(temp_dir, "README.md")
            self._generate_readme(app, config_data, readme_file)
            files_to_zip.append(readme_file)

            # 打包
            with zipfile.ZipFile(filepath, "w", zipfile.ZIP_DEFLATED) as zf:
                for file_path in files_to_zip:
                    arcname = os.path.basename(file_path)
                    zf.write(file_path, arcname)

        # 计算文件信息
        file_size = os.path.getsize(filepath)
        checksum = self._calculate_checksum(filepath)

        result = {
            "version": version,
            "file_path": filepath,
            "file_name": filename,
            "file_size": file_size,
            "checksum": checksum
        }

        self._log_info(f"配置包生成成功: {filename}", result)
        return result

    def _build_config_data(self, app) -> Dict[str, Any]:
        """
        构建配置数据

        Args:
            app: Application 实例

        Returns:
            配置数据字典
        """
        config = {
            "app": {
                "id": app.id,
                "name": app.name,
                "code": app.code,
                "type": app.app_type,
                "description": app.description,
            },
            "project": {
                "id": app.project.id,
                "name": app.project.name,
                "code": app.project.code,
            },
            "module": {
                "id": app.module.id,
                "name": app.module.name,
                "code": app.module.code,
            },
            "git": {
                "url": app.git_url,
                "branch": app.build_branch,
                "dockerfile_path": app.dockerfile_path,
            },
            "devops": {
                "gitlab_project_id": app.gitlab_project_id,
                "harbor_project": app.harbor_project,
            },
            "generated_at": datetime.now().isoformat()
        }

        return config

    def _get_template_files(self, app_type: str, temp_dir: str) -> list:
        return []

    def _generate_readme(self, app, config: dict, filepath: str):
        """生成 README 文件"""
        content = f"""# {app.name} 配置包

## 基本信息

- **项目**: {app.project.name} ({app.project.code})
- **模块**: {app.module.name} ({app.module.code})
- **应用**: {app.name} ({app.code})
- **类型**: {app.app_type}

## Git 信息

- **仓库地址**: {app.git_url or '未配置'}
- **构建分支**: {app.build_branch}
- **Dockerfile路径**: {app.dockerfile_path}

## DevOps 信息

- **GitLab Project ID**: {app.gitlab_project_id or '未创建'}
- **Harbor Project**: {app.harbor_project or '未创建'}

## 文件说明

- `config.json` - 应用配置信息
- `Jenkinsfile` - Jenkins Pipeline 配置（如存在）
- `Dockerfile` - Docker 构建配置（如存在）

## 生成信息

- 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

    def _calculate_checksum(self, filepath: str) -> str:
        """计算文件校验和"""
        sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def upload_package(self, local_path: str, remote_path: str = None) -> str:
        """
        上传配置包到文件服务器

        Args:
            local_path: 本地文件路径
            remote_path: 远程路径，默认使用文件名

        Returns:
            远程文件路径
        """
        if not os.path.exists(local_path):
            self._handle_error(f"文件不存在: {local_path}")

        filename = os.path.basename(local_path)
        if not remote_path:
            remote_path = f"config_packages/{filename}"

        try:
            with open(local_path, "rb") as f:
                saved_path = default_storage.save(remote_path, f)

            self._log_info(f"配置包上传成功: {saved_path}")
            return saved_path
        except Exception as e:
            self._handle_error(f"配置包上传失败: {str(e)}")

    def cleanup_old_packages(self, app_id: int, keep_count: int = 10):
        """
        清理旧配置包，保留最新的 N 个

        Args:
            app_id: 应用 ID
            keep_count: 保留数量
        """
        from ..models import ConfigPackage

        packages = ConfigPackage.objects.filter(app_id=app_id, is_deleted=False).order_by("-create_time")
        total = packages.count()

        if total <= keep_count:
            return

        # 软删除多余的包
        to_delete = packages[keep_count:]
        for pkg in to_delete:
            pkg.is_deleted = True
            pkg.save(update_fields=["is_deleted"])

        self._log_info(f"清理旧配置包: 应用 {app_id}, 删除 {len(to_delete)} 个")
