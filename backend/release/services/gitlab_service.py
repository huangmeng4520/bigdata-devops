# -*- coding: utf-8 -*-
"""
GitLab API 服务
封装 GitLab Group/Subgroup/Project 的创建和管理
"""
import logging
import requests
from typing import Optional, Dict, Any
from .base import BaseService, ConfigService, DevOpsException

logger = logging.getLogger(__name__)


class GitLabService(BaseService):
    """GitLab API 服务"""

    service_name = "gitlab"

    # HTTP 超时配置
    CONNECT_TIMEOUT = 5
    READ_TIMEOUT = 30

    def __init__(self):
        super().__init__()
        self._init_config()

    def _init_config(self):
        """初始化配置"""
        config = ConfigService.get_gitlab_config()
        self.url = config.get(ConfigService.GITLAB_URL, "").rstrip("/")
        self.token = config.get(ConfigService.GITLAB_TOKEN, "")
        self.root_group_id = config.get(ConfigService.GITLAB_ROOT_GROUP)

        if not self.url or not self.token:
            self._log_warning("GitLab 配置不完整，服务可能无法正常工作")

    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        return {
            "Private-Token": self.token,
            "Content-Type": "application/json"
        }

    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        发送请求到 GitLab API

        Args:
            method: HTTP 方法
            endpoint: API 端点
            **kwargs: requests 参数

        Returns:
            响应 JSON

        Raises:
            DevOpsException: 请求失败
        """
        url = f"{self.url}/api/v4{endpoint}"
        kwargs.setdefault("headers", self._get_headers())
        kwargs.setdefault("timeout", (self.CONNECT_TIMEOUT, self.READ_TIMEOUT))

        try:
            response = requests.request(method, url, **kwargs)
            
            # Debug logging
            logger.debug(f"GitLab API: {method} {url} -> {response.status_code}")

            if response.status_code == 401:
                self._handle_error("GitLab 认证失败，请检查 Token", {"status_code": 401})

            if response.status_code == 403:
                self._handle_error("GitLab 权限不足", {"status_code": 403})

            if response.status_code >= 400:
                try:
                    error_data = response.json()
                    error_msg = error_data.get("message") or error_data.get("error", "未知错误")
                except Exception:
                    error_msg = response.text[:200] if response.text else "未知错误"
                self._handle_error(f"GitLab API 请求失败: {error_msg}", {
                    "status_code": response.status_code,
                    "response": response.text[:500] if response.text else ""
                })

            if response.status_code == 204:
                return {}

            return response.json()

        except requests.exceptions.Timeout:
            self._handle_error("GitLab API 请求超时")
        except requests.exceptions.ConnectionError:
            self._handle_error("无法连接 GitLab 服务")
        except requests.exceptions.RequestException as e:
            self._handle_error(f"GitLab API 请求异常: {str(e)}")

    # ==================== Group 操作 ====================

    def group_exists(self, path: str) -> bool:
        """
        检查 Group 是否存在

        Args:
            path: Group 路径

        Returns:
            是否存在
        """
        try:
            result = self._request("GET", f"/groups/{path}")
            return True
        except DevOpsException:
            return False

    def get_group(self, path: str) -> Optional[Dict[str, Any]]:
        """
        获取 Group 信息

        Args:
            path: Group 路径

        Returns:
            Group 信息或 None
        """
        try:
            return self._request("GET", f"/groups/{path}")
        except DevOpsException:
            return None

    def create_group(self, name: str, path: str, parent_id: int = None, **kwargs) -> Dict[str, Any]:
        """
        创建 GitLab Group

        Args:
            name: Group 名称
            path: Group 路径
            parent_id: 父 Group ID（创建 Subgroup 时使用）
            **kwargs: 其他参数（visibility, description 等）

        Returns:
            创建的 Group 信息
        """
        # 幂等性检查：先检查是否已存在
        full_path = path
        if parent_id:
            parent = self.get_group_by_id(parent_id)
            if parent:
                full_path = f"{parent['full_path']}/{path}"

        existing = self.get_group(full_path)
        if existing:
            self._log_info(f"GitLab Group 已存在: {full_path}", {"id": existing["id"]})
            return existing

        data = {
            "name": name,
            "path": path,
            "visibility": kwargs.get("visibility", "private"),
            "request_access_enabled": False,
            **kwargs
        }

        if parent_id:
            data["parent_id"] = parent_id

        self._log_info(f"创建 GitLab Group: {name}", {"path": path, "parent_id": parent_id})
        result = self._request("POST", "/groups", json=data)

        self._log_info(f"GitLab Group 创建成功", {"id": result["id"], "full_path": result["full_path"]})
        return result

    def get_group_by_id(self, group_id: int) -> Optional[Dict[str, Any]]:
        """
        根据 ID 获取 Group

        Args:
            group_id: Group ID

        Returns:
            Group 信息或 None
        """
        try:
            return self._request("GET", f"/groups/{group_id}")
        except DevOpsException:
            return None

    # ==================== Project 操作 ====================

    def project_exists(self, namespace_id: int, path: str) -> bool:
        """
        检查 Project 是否存在

        Args:
            namespace_id: 命名空间 ID
            path: Project 路径

        Returns:
            是否存在
        """
        try:
            # 通过搜索检查
            result = self._request("GET", "/projects", params={
                "search": path,
                "namespace_id": namespace_id
            })
            for project in result:
                if project.get("path") == path:
                    return True
            return False
        except DevOpsException:
            return False

    def get_project(self, project_id: int) -> Optional[Dict[str, Any]]:
        """
        获取 Project 信息

        Args:
            project_id: Project ID

        Returns:
            Project 信息或 None
        """
        try:
            return self._request("GET", f"/projects/{project_id}")
        except DevOpsException:
            return None

    def get_project_by_path(self, path: str) -> Optional[Dict[str, Any]]:
        """
        通过路径获取 Project

        Args:
            path: 项目完整路径 (group/subgroup/project)

        Returns:
            Project 信息或 None
        """
        try:
            encoded_path = requests.utils.quote(path, safe='')
            return self._request("GET", f"/projects/{encoded_path}")
        except DevOpsException:
            return None

    def create_project(self, name: str, path: str, namespace_id: int, **kwargs) -> Dict[str, Any]:
        """
        创建 GitLab Project

        Args:
            name: Project 名称
            path: Project 路径
            namespace_id: 命名空间 ID（Group/Subgroup ID）
            **kwargs: 其他参数

        Returns:
            创建的 Project 信息
        """
        # 幂等性检查：先检查是否已存在
        namespace = self.get_group_by_id(namespace_id)
        if namespace:
            full_path = f"{namespace['full_path']}/{path}"
            existing = self.get_project_by_path(full_path)
            if existing:
                self._log_info(f"GitLab Project 已存在: {full_path}", {"id": existing["id"]})
                return existing

        data = {
            "name": name,
            "path": path,
            "namespace_id": namespace_id,
            "visibility": kwargs.get("visibility", "private"),
            "initialize_with_readme": kwargs.get("initialize_with_readme", True),
            "default_branch": kwargs.get("default_branch", "main"),
            # CI/CD 配置
            "builds_access_level": "enabled",
            "container_registry_enabled": True,
            # 禁用不需要的功能
            "wiki_enabled": False,
            "snippets_enabled": False,
            "issues_enabled": True,
            "merge_requests_enabled": True,
            **kwargs
        }

        self._log_info(f"创建 GitLab Project: {name}", {"path": path, "namespace_id": namespace_id})
        result = self._request("POST", "/projects", json=data)

        self._log_info(f"GitLab Project 创建成功", {
            "id": result["id"],
            "path_with_namespace": result["path_with_namespace"],
            "web_url": result["web_url"]
        })
        return result

    def get_project_ssh_url(self, project_id: int) -> Optional[str]:
        """获取项目的 SSH Git URL"""
        project = self.get_project(project_id)
        if project:
            return project.get("ssh_url_to_repo")
        return None

    def get_project_http_url(self, project_id: int) -> Optional[str]:
        """获取项目的 HTTP Git URL"""
        project = self.get_project(project_id)
        if project:
            return project.get("http_url_to_repo")
        return None

    # ==================== 辅助方法 ====================

    def create_project_with_structure(
        self,
        project_name: str,
        project_path: str,
        group_path: str,
        group_id: int = None
    ) -> Dict[str, Any]:
        """
        在指定 Group 下创建 Project

        Args:
            project_name: Project 名称
            project_path: Project 路径
            group_path: Group 路径（用于查找）
            group_id: Group ID（如果已知）

        Returns:
            创建的 Project 信息
        """
        # 获取或创建 Group
        if not group_id:
            group = self.get_group(group_path)
            if not group:
                raise DevOpsException(f"Group 不存在: {group_path}", service=self.service_name)
            group_id = group["id"]

        return self.create_project(project_name, project_path, group_id)

    def test_connection(self) -> bool:
        """
        测试 GitLab 连接

        Returns:
            连接是否成功
        """
        try:
            self._request("GET", "/user")
            self._log_info("GitLab 连接测试成功")
            return True
        except DevOpsException as e:
            self._log_warning(f"GitLab 连接测试失败: {e.message}")
            return False

    # ==================== 导入 GitLab 资源 ====================

    def list_groups(self, page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        """
        获取 GitLab Groups 列表

        Args:
            page: 页码
            per_page: 每页数量

        Returns:
            Groups 列表和总数
        """
        result = self._request("GET", "/groups", params={
            "page": page,
            "per_page": per_page,
            "all_available": True
        })
        return result

    def list_subgroups(self, parent_id: int, page: int = 1, per_page: int = 20) -> list:
        """
        获取 Subgroups 列表

        Args:
            parent_id: 父 Group ID
            page: 页码
            per_page: 每页数量

        Returns:
            Subgroups 列表
        """
        result = self._request("GET", f"/groups/{parent_id}/subgroups", params={
            "page": page,
            "per_page": per_page
        })
        return result

    def list_projects(self, group_id: int = None, page: int = 1, per_page: int = 20) -> list:
        """
        获取 GitLab Projects 列表

        Args:
            group_id: Group ID（可选，不传则获取所有有权限的项目）
            page: 页码
            per_page: 每页数量

        Returns:
            Projects 列表
        """
        params = {
            "page": page,
            "per_page": per_page,
            "order_by": "last_activity_at",
            "sort": "desc"
        }
        if group_id:
            params["group_id"] = group_id
        
        result = self._request("GET", "/projects", params=params)
        return result

    def search_groups(self, search: str, page: int = 1, per_page: int = 20) -> list:
        """
        搜索 Groups

        Args:
            search: 搜索关键词
            page: 页码
            per_page: 每页数量

        Returns:
            匹配的 Groups 列表
        """
        result = self._request("GET", "/groups", params={
            "search": search,
            "page": page,
            "per_page": per_page,
            "all_available": True
        })
        return result

    def search_projects(self, search: str, page: int = 1, per_page: int = 20) -> list:
        """
        搜索 Projects

        Args:
            search: 搜索关键词
            page: 页码
            per_page: 每页数量

        Returns:
            匹配的 Projects 列表
        """
        result = self._request("GET", "/projects", params={
            "search": search,
            "page": page,
            "per_page": per_page
        })
        return result
