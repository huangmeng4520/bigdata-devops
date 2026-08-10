# -*- coding: utf-8 -*-
"""
服务层基础类和配置获取服务
"""
import logging
from typing import Optional, Dict, Any
from django.core.cache import cache
from system.models import Config

logger = logging.getLogger(__name__)


class DevOpsException(Exception):
    """DevOps 服务异常基类"""

    def __init__(self, message: str, service: str = None, details: Any = None):
        self.message = message
        self.service = service
        self.details = details
        super().__init__(self.message)

    def __str__(self):
        if self.service:
            return f"[{self.service}] {self.message}"
        return self.message


class ConfigService:
    """
    配置获取服务
    从 system_config 表获取配置，支持缓存
    """

    CACHE_PREFIX = "devops_config:"
    CACHE_TIMEOUT = 300  # 5分钟缓存

    # 配置键名常量
    GITLAB_URL = "gitlab_url"                  # 后端内网调用 GitLab API 用的地址
    GITLAB_EXTERNAL_URL = "gitlab_external_url"  # 前端浏览器展示/跳转用的外网地址（缺省时回退到 GITLAB_URL）
    GITLAB_TOKEN = "gitlab_token"
    GITLAB_ROOT_GROUP = "gitlab_root_group"

    JENKINS_URL = "jenkins_url"
    JENKINS_USER = "jenkins_user"
    JENKINS_TOKEN = "jenkins_token"

    HARBOR_URL = "harbor_url"
    HARBOR_USER = "harbor_user"
    HARBOR_PASSWORD = "harbor_password"

    CONFIG_PACKAGE_PATH = "config_package_path"

    @classmethod
    def get(cls, key: str, default: str = None, use_cache: bool = True) -> Optional[str]:
        """
        获取配置值

        Args:
            key: 配置键名
            default: 默认值
            use_cache: 是否使用缓存

        Returns:
            配置值或默认值
        """
        cache_key = f"{cls.CACHE_PREFIX}{key}"

        if use_cache:
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value

        try:
            config = Config.objects.filter(key=key, is_deleted=False).first()
            if config:
                value = config.value
                if use_cache:
                    cache.set(cache_key, value, cls.CACHE_TIMEOUT)
                return value
        except Exception as e:
            logger.warning(f"获取配置失败: {key}, 错误: {e}")

        return default

    @classmethod
    def get_all(cls, keys: list, use_cache: bool = True) -> Dict[str, str]:
        """
        批量获取配置

        Args:
            keys: 配置键名列表
            use_cache: 是否使用缓存

        Returns:
            配置字典
        """
        result = {}
        for key in keys:
            result[key] = cls.get(key, default="", use_cache=use_cache)
        return result

    @classmethod
    def get_gitlab_config(cls) -> Dict[str, str]:
        """获取 GitLab 配置"""
        return cls.get_all([
            cls.GITLAB_URL,
            cls.GITLAB_EXTERNAL_URL,
            cls.GITLAB_TOKEN,
            cls.GITLAB_ROOT_GROUP,
        ])

    @classmethod
    def get_gitlab_external_url(cls, use_cache: bool = True) -> str:
        """
        获取 GitLab 外网展示地址（用于拼接给前端用户点击跳转的 Web URL）。
        若未配置 gitlab_external_url，则回退到 gitlab_url，保证未分离场景下行为不变。

        Returns:
            外网地址（已去除末尾斜杠），可能为空字符串
        """
        external = cls.get(cls.GITLAB_EXTERNAL_URL, default="", use_cache=use_cache).rstrip("/")
        if external:
            return external
        return cls.get(cls.GITLAB_URL, default="", use_cache=use_cache).rstrip("/")

    @classmethod
    def get_jenkins_config(cls) -> Dict[str, str]:
        """获取 Jenkins 配置"""
        return cls.get_all([cls.JENKINS_URL, cls.JENKINS_USER, cls.JENKINS_TOKEN])

    @classmethod
    def get_harbor_config(cls) -> Dict[str, str]:
        """获取 Harbor 配置"""
        return cls.get_all([cls.HARBOR_URL, cls.HARBOR_USER, cls.HARBOR_PASSWORD])

    @classmethod
    def clear_cache(cls, key: str = None):
        """
        清除配置缓存

        Args:
            key: 配置键名，为 None 时清除所有
        """
        if key:
            cache.delete(f"{cls.CACHE_PREFIX}{key}")
        else:
            # 清除所有 devops 配置缓存
            keys = [
                cls.GITLAB_URL, cls.GITLAB_EXTERNAL_URL, cls.GITLAB_TOKEN, cls.GITLAB_ROOT_GROUP,
                cls.JENKINS_URL, cls.JENKINS_USER, cls.JENKINS_TOKEN,
                cls.HARBOR_URL, cls.HARBOR_USER, cls.HARBOR_PASSWORD,
                cls.CONFIG_PACKAGE_PATH
            ]
            for k in keys:
                cache.delete(f"{cls.CACHE_PREFIX}{k}")


class BaseService:
    """
    服务基类
    提供公共方法和错误处理
    """

    service_name = "base"

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.service_name}")

    def _handle_error(self, message: str, details: Any = None) -> None:
        """处理错误，记录日志并抛出异常"""
        self.logger.error(f"[{self.service_name}] {message}", extra={"details": details})
        raise DevOpsException(message, service=self.service_name, details=details)

    def _log_info(self, message: str, details: Any = None) -> None:
        """记录信息日志"""
        self.logger.info(f"[{self.service_name}] {message}", extra={"details": details})

    def _log_warning(self, message: str, details: Any = None) -> None:
        """记录警告日志"""
        self.logger.warning(f"[{self.service_name}] {message}", extra={"details": details})

    def _log_error(self, message: str, details: Any = None) -> None:
        """记录错误日志"""
        self.logger.error(f"[{self.service_name}] {message}", extra={"details": details})
