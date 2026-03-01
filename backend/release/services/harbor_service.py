# -*- coding: utf-8 -*-
"""
Harbor API 服务
封装 Harbor Project 的创建和管理
"""
import requests
from typing import Optional, Dict, Any
import urllib3
from .base import BaseService, ConfigService, DevOpsException

# 禁用自签名证书的 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class HarborService(BaseService):
    """Harbor API 服务"""

    service_name = "harbor"

    # HTTP 超时配置
    CONNECT_TIMEOUT = 5
    READ_TIMEOUT = 30

    def __init__(self):
        super().__init__()
        self._init_config()

    def _init_config(self):
        """初始化配置"""
        config = ConfigService.get_harbor_config()
        self.url = config.get(ConfigService.HARBOR_URL, "").rstrip("/")
        self.user = config.get(ConfigService.HARBOR_USER, "")
        self.password = config.get(ConfigService.HARBOR_PASSWORD, "")

        if not self.url or not self.user or not self.password:
            self._log_warning("Harbor 配置不完整，服务可能无法正常工作")

    def _get_auth(self) -> tuple:
        """获取认证信息"""
        return (self.user, self.password)

    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        return {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        发送请求到 Harbor API

        Args:
            method: HTTP 方法
            endpoint: API 端点
            **kwargs: requests 参数

        Returns:
            响应 JSON

        Raises:
            DevOpsException: 请求失败
        """
        url = f"{self.url}/api/v2.0{endpoint}"
        kwargs.setdefault("auth", self._get_auth())
        kwargs.setdefault("headers", self._get_headers())
        kwargs.setdefault("timeout", (self.CONNECT_TIMEOUT, self.READ_TIMEOUT))
        kwargs.setdefault("verify", False)  # 禁用 SSL 证书验证（支持自签名证书）

        try:
            response = requests.request(method, url, **kwargs)

            if response.status_code == 401:
                self._handle_error("Harbor 认证失败，请检查用户名和密码", {"status_code": 401})

            if response.status_code == 403:
                self._handle_error("Harbor 权限不足", {"status_code": 403})

            # Harbor 返回 201 表示创建成功，可能没有内容
            if response.status_code == 201:
                # 尝试从 Location header 获取资源 ID
                location = response.headers.get("Location", "")
                return {"created": True, "location": location}

            if response.status_code >= 400:
                error_msg = "未知错误"
                try:
                    errors = response.json().get("errors", [])
                    if errors:
                        error_msg = errors[0].get("message", error_msg)
                except Exception:
                    error_msg = response.text[:200] if response.text else error_msg

                self._handle_error(f"Harbor API 请求失败: {error_msg}", {
                    "status_code": response.status_code,
                    "response": response.text[:500]
                })

            if response.status_code == 204:
                return {}

            return response.json()

        except requests.exceptions.Timeout:
            self._handle_error("Harbor API 请求超时")
        except requests.exceptions.ConnectionError:
            self._handle_error("无法连接 Harbor 服务")
        except requests.exceptions.RequestException as e:
            self._handle_error(f"Harbor API 请求异常: {str(e)}")

    # ==================== Project 操作 ====================

    def project_exists(self, name: str) -> bool:
        """
        检查 Project 是否存在

        Args:
            name: Project 名称

        Returns:
            是否存在
        """
        try:
            result = self._request("GET", f"/projects/{name}")
            return True
        except DevOpsException:
            return False

    def get_project(self, name_or_id) -> Optional[Dict[str, Any]]:
        """
        获取 Project 信息

        Args:
            name_or_id: Project 名称或 ID

        Returns:
            Project 信息或 None
        """
        try:
            return self._request("GET", f"/projects/{name_or_id}")
        except DevOpsException:
            return None

    def create_project(self, name: str, **kwargs) -> Dict[str, Any]:
        """
        创建 Harbor Project

        Args:
            name: Project 名称
            **kwargs: 其他参数

        Returns:
            创建结果
        """
        # 幂等性检查
        existing = self.get_project(name)
        if existing:
            self._log_info(f"Harbor Project 已存在: {name}", {"project_id": existing["project_id"]})
            return existing

        # Project 创建参数
        data = {
            "project_name": name,
            "public": kwargs.get("public", False),
            "metadata": {
                "public": "false"
            },
            "storage_limit": kwargs.get("storage_limit", -1),  # -1 表示无限制
            "registry_id": kwargs.get("registry_id", None)
        }

        self._log_info(f"创建 Harbor Project: {name}")
        result = self._request("POST", "/projects", json=data)

        self._log_info(f"Harbor Project 创建成功: {name}")

        # 获取创建后的 Project 信息
        created = self.get_project(name)
        return created if created else result

    # ==================== Robot Account 操作 ====================

    def create_robot_account(
        self,
        project_name: str,
        robot_name: str,
        duration: int = 30,
        permissions: list = None
    ) -> Optional[Dict[str, Any]]:
        """
        创建机器人账号

        Args:
            project_name: Project 名称
            robot_name: Robot 名称
            duration: 有效期（天）
            permissions: 权限列表

        Returns:
            Robot 信息（包含 token）
        """
        # 检查 project
        project = self.get_project(project_name)
        if not project:
            self._handle_error(f"Project 不存在: {project_name}")

        project_id = project["project_id"]

        # 默认权限：推送和拉取
        if not permissions:
            permissions = [
                {
                    "access": [
                        {"action": "push", "resource": "repository"},
                        {"action": "pull", "resource": "repository"},
                        {"action": "push", "resource": "helm-chart"},
                        {"action": "pull", "resource": "helm-chart-version"}
                    ],
                    "kind": "project",
                    "namespace": project_name
                }
            ]

        data = {
            "name": robot_name,
            "duration": duration,
            "description": f"Robot account for {project_name}",
            "permissions": permissions,
            "disable": False
        }

        self._log_info(f"创建 Robot Account: {robot_name}", {"project": project_name})

        try:
            result = self._request("POST", f"/projects/{project_id}/robots", json=data)
            self._log_info(f"Robot Account 创建成功: {robot_name}")
            return result
        except DevOpsException as e:
            self._log_warning(f"创建 Robot Account 失败: {e.message}")
            return None

    def get_robot_accounts(self, project_name: str) -> list:
        """
        获取 Project 的所有 Robot Accounts

        Args:
            project_name: Project 名称

        Returns:
            Robot Account 列表
        """
        project = self.get_project(project_name)
        if not project:
            return []

        try:
            result = self._request("GET", f"/projects/{project['project_id']}/robots")
            return result
        except DevOpsException:
            return []

    # ==================== 辅助方法 ====================

    def create_project_with_robot(
        self,
        name: str,
        robot_suffix: str = "ci"
    ) -> Dict[str, Any]:
        """
        创建 Project 并创建 Robot Account

        Args:
            name: Project 名称
            robot_suffix: Robot 名称后缀

        Returns:
            创建结果
        """
        result = {
            "project": None,
            "robot": None
        }

        # 创建 Project
        project = self.create_project(name)
        result["project"] = project

        # 创建 Robot Account
        robot_name = f"{name}-{robot_suffix}"
        robot = self.create_robot_account(name, robot_name)
        result["robot"] = robot

        return result

    def get_registry_url(self) -> str:
        """
        获取 Docker Registry URL

        Returns:
            Registry URL
        """
        # 从 Harbor URL 提取 registry 地址
        # 例如: https://harbor.example.com -> harbor.example.com
        url = self.url
        if url.startswith("https://"):
            return url[8:]
        elif url.startswith("http://"):
            return url[7:]
        return url

    def test_connection(self) -> bool:
        """
        测试 Harbor 连接

        Returns:
            连接是否成功
        """
        try:
            self._request("GET", "/projects")
            self._log_info("Harbor 连接测试成功")
            return True
        except DevOpsException as e:
            self._log_warning(f"Harbor 连接测试失败: {e.message}")
            return False

    # ==================== Webhook 操作 ====================

    def create_webhook(
        self,
        project_name: str,
        webhook_url: str,
        events: list = None
    ) -> Optional[Dict[str, Any]]:
        """
        创建 Webhook

        Args:
            project_name: Project 名称
            webhook_url: Webhook URL
            events: 事件类型列表

        Returns:
            Webhook 信息
        """
        project = self.get_project(project_name)
        if not project:
            self._handle_error(f"Project 不存在: {project_name}")

        if not events:
            events = ["PUSH_ARTIFACT", "PULL_ARTIFACT", "DELETE_ARTIFACT"]

        data = {
            "targets": [
                {
                    "type": "http",
                    "address": webhook_url,
                    "skip_cert_verify": True
                }
            ],
            "event_types": events,
            "enabled": True
        }

        self._log_info(f"创建 Webhook: {webhook_url}", {"project": project_name})

        try:
            result = self._request(
                "POST",
                f"/projects/{project['project_id']}/webhook/policies",
                json=data
            )
            self._log_info("Webhook 创建成功")
            return result
        except DevOpsException as e:
            self._log_warning(f"创建 Webhook 失败: {e.message}")
            return None
