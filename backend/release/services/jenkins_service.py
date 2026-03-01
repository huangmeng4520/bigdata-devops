# -*- coding: utf-8 -*-
"""
Jenkins API 服务
封装 Jenkins Job/Folder 的创建和管理
"""
import requests
from requests.auth import HTTPBasicAuth
from xml.etree import ElementTree
from typing import Optional, Dict, Any, List
from .base import BaseService, ConfigService, DevOpsException


class JenkinsService(BaseService):
    """Jenkins API 服务"""

    service_name = "jenkins"

    # HTTP 超时配置
    CONNECT_TIMEOUT = 5
    READ_TIMEOUT = 60  # Jenkins 操作可能较慢

    def __init__(self):
        super().__init__()
        self._init_config()

    def _init_config(self):
        """初始化配置"""
        config = ConfigService.get_jenkins_config()
        self.url = config.get(ConfigService.JENKINS_URL, "").rstrip("/")
        self.user = config.get(ConfigService.JENKINS_USER, "")
        self.token = config.get(ConfigService.JENKINS_TOKEN, "")

        if not self.url or not self.user or not self.token:
            self._log_warning("Jenkins 配置不完整，服务可能无法正常工作")

    def _get_auth(self) -> HTTPBasicAuth:
        """获取认证信息"""
        return HTTPBasicAuth(self.user, self.token)

    def _get_crumb(self) -> Optional[str]:
        """获取 CSRF Crumb"""
        try:
            response = requests.get(
                f"{self.url}/crumbIssuer/api/json",
                auth=self._get_auth(),
                timeout=(self.CONNECT_TIMEOUT, self.READ_TIMEOUT)
            )
            if response.status_code == 200:
                data = response.json()
                return f"{data['crumbRequestField']}={data['crumb']}"
        except Exception:
            pass
        return None

    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        headers = {"Content-Type": "application/xml; charset=utf-8"}
        crumb = self._get_crumb()
        if crumb:
            field, value = crumb.split("=")
            headers[field] = value
        return headers

    def _build_job_path(self, folder: str = None) -> str:
        """
        构建 Jenkins Job 路径

        Jenkins API 要求每个 folder 前加 /job
        例如: "project/module" -> "/job/project/job/module"

        Args:
            folder: folder 路径，如 "project/module"

        Returns:
            正确的 Jenkins 路径
        """
        if not folder:
            return ""
        # 将 "a/b/c" 转换为 "/job/a/job/b/job/c"
        parts = folder.strip("/").split("/")
        return "/job/" + "/job/".join(parts)

    def _request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """
        发送请求到 Jenkins API

        Args:
            method: HTTP 方法
            endpoint: API 端点
            **kwargs: requests 参数

        Returns:
            Response 对象

        Raises:
            DevOpsException: 请求失败
        """
        url = f"{self.url}{endpoint}"
        kwargs.setdefault("auth", self._get_auth())
        kwargs.setdefault("headers", self._get_headers())
        kwargs.setdefault("timeout", (self.CONNECT_TIMEOUT, self.READ_TIMEOUT))

        try:
            response = requests.request(method, url, **kwargs)

            if response.status_code == 401:
                self._handle_error("Jenkins 认证失败，请检查用户名和 Token", {"status_code": 401})

            if response.status_code == 403:
                self._handle_error("Jenkins 权限不足", {"status_code": 403})

            return response

        except requests.exceptions.Timeout:
            self._handle_error("Jenkins API 请求超时")
        except requests.exceptions.ConnectionError:
            self._handle_error("无法连接 Jenkins 服务")
        except requests.exceptions.RequestException as e:
            self._handle_error(f"Jenkins API 请求异常: {str(e)}")

    # ==================== Folder 操作 ====================

    def folder_exists(self, name: str, parent: str = None) -> bool:
        """
        检查 Folder 是否存在

        Args:
            name: Folder 名称
            parent: 父 Folder 路径（如 "project/module"）

        Returns:
            是否存在
        """
        parent_path = self._build_job_path(parent) if parent else ""
        path = f"{parent_path}/job/{name}" if parent else f"/job/{name}"
        response = self._request("GET", f"{path}/api/json")
        return response.status_code == 200

    def create_folder(self, name: str, parent: str = None) -> bool:
        """
        创建 Jenkins Folder

        Args:
            name: Folder 名称
            parent: 父 Folder 路径

        Returns:
            是否创建成功
        """
        # 幂等性检查
        if self.folder_exists(name, parent):
            self._log_info(f"Jenkins Folder 已存在: {name}", {"parent": parent})
            return True

        # Folder XML 配置
        folder_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<com.cloudbees.hudson.plugins.folder.Folder plugin="cloudbees-folder">
  <description></description>
  <properties/>
  <folderViews class="com.cloudbees.hudson.plugins.folder.views.DefaultFolderViewHolderImpl">
    <views>
      <hudson.model.AllView>
        <owner class="com.cloudbees.hudson.plugins.folder.Folder" reference="../../../.."/>
        <name>All</name>
        <filterExecutors>false</filterExecutors>
        <filterQueue>false</filterQueue>
        <properties class="hudson.model.View$PropertyList"/>
      </hudson.model.AllView>
    </views>
    <tabBar class="hudson.views.DefaultViewsTabBar"/>
  </folderViews>
  <healthMetrics/>
</com.cloudbees.hudson.plugins.folder.Folder>'''

        endpoint = f"{self._build_job_path(parent)}/createItem?name={name}" if parent else f"/createItem?name={name}"

        self._log_info(f"创建 Jenkins Folder: {name}", {"parent": parent})
        response = self._request("POST", endpoint, data=folder_xml.encode("utf-8"))

        if response.status_code in [200, 201, 302]:
            self._log_info(f"Jenkins Folder 创建成功: {name}")
            return True
        elif response.status_code == 400:
            # 可能已存在
            if self.folder_exists(name, parent):
                return True
            self._handle_error(f"创建 Jenkins Folder 失败", {"response": response.text[:500]})
        else:
            self._handle_error(f"创建 Jenkins Folder 失败", {
                "status_code": response.status_code,
                "response": response.text[:500]
            })

        return False

    # ==================== Pipeline Job 操作 ====================

    def job_exists(self, name: str, folder: str = None) -> bool:
        """
        检查 Job 是否存在

        Args:
            name: Job 名称
            folder: Folder 路径

        Returns:
            是否存在
        """
        folder_path = self._build_job_path(folder) if folder else ""
        path = f"{folder_path}/job/{name}" if folder else f"/job/{name}"
        response = self._request("GET", f"{path}/api/json")
        return response.status_code == 200

    def create_pipeline_job(
        self,
        name: str,
        folder: str = None,
        git_url: str = None,
        branch: str = "main",
        jenkinsfile_path: str = "Jenkinsfile",
        description: str = ""
    ) -> bool:
        """
        创建 Pipeline Job

        Args:
            name: Job 名称
            folder: Folder 路径
            git_url: Git 仓库地址
            branch: 分支
            jenkinsfile_path: Jenkinsfile 路径
            description: 描述

        Returns:
            是否创建成功
        """
        # 幂等性检查
        if self.job_exists(name, folder):
            self._log_info(f"Jenkins Job 已存在: {name}", {"folder": folder})
            return True

        # Pipeline Job XML 配置
        job_xml = self._generate_pipeline_xml(
            git_url=git_url,
            branch=branch,
            jenkinsfile_path=jenkinsfile_path,
            description=description
        )

        endpoint = f"{self._build_job_path(folder)}/createItem?name={name}" if folder else f"/createItem?name={name}"

        self._log_info(f"创建 Jenkins Pipeline: {name}", {
            "folder": folder,
            "git_url": git_url,
            "branch": branch
        })

        response = self._request("POST", endpoint, data=job_xml.encode("utf-8"))

        if response.status_code in [200, 201, 302]:
            self._log_info(f"Jenkins Pipeline 创建成功: {name}")
            return True
        elif response.status_code == 400:
            if self.job_exists(name, folder):
                return True
            self._handle_error(f"创建 Jenkins Pipeline 失败", {"response": response.text[:500]})
        else:
            self._handle_error(f"创建 Jenkins Pipeline 失败", {
                "status_code": response.status_code,
                "response": response.text[:500]
            })

        return False

    def _generate_pipeline_xml(
        self,
        git_url: str = None,
        branch: str = "main",
        jenkinsfile_path: str = "Jenkinsfile",
        description: str = ""
    ) -> str:
        """生成 Pipeline Job XML 配置"""
        # 基础 Pipeline 模板
        if git_url:
            return f'''<?xml version="1.0" encoding="UTF-8"?>
<flow-definition plugin="workflow-job">
  <description>{description}</description>
  <definition class="org.jenkinsci.plugins.workflow.cps.CpsScmFlowDefinition" plugin="workflow-cps">
    <scm class="hudson.plugins.git.GitSCM" plugin="git">
      <configVersion>2</configVersion>
      <userRemoteConfigs>
        <hudson.plugins.git.UserRemoteConfig>
          <url>{git_url}</url>
        </hudson.plugins.git.UserRemoteConfig>
      </userRemoteConfigs>
      <branches>
        <hudson.plugins.git.BranchSpec>
          <name>*/{branch}</name>
        </hudson.plugins.git.BranchSpec>
      </branches>
      <doGenerateSubmoduleConfigurations>false</doGenerateSubmoduleConfigurations>
      <submoduleCfg class="empty-list"/>
      <extensions/>
    </scm>
    <scriptPath>{jenkinsfile_path}</scriptPath>
    <lightweight>true</lightweight>
  </definition>
  <triggers/>
  <disabled>false</disabled>
</flow-definition>'''
        else:
            # 没有 Git URL，使用内联脚本
            return f'''<?xml version="1.0" encoding="UTF-8"?>
<flow-definition plugin="workflow-job">
  <description>{description}</description>
  <definition class="org.jenkinsci.plugins.workflow.cps.CpsFlowDefinition" plugin="workflow-cps">
    <script>pipeline {{
    agent any
    stages {{
        stage('Build') {{
            steps {{
                echo 'Building...'
            }}
        }}
    }}
}}</script>
    <sandbox>true</sandbox>
  </definition>
  <triggers/>
  <disabled>false</disabled>
</flow-definition>'''

    # ==================== 批量创建 ====================

    def create_ci_cd_jobs(
        self,
        project_code: str,
        module_code: str,
        app_code: str,
        git_url: str,
        branch: str = "main"
    ) -> Dict[str, bool]:
        """
        创建 CI/CD Jobs

        按照命名规范创建：
        - 项目目录: {project_code}
        - 模块目录: {project_code}/{module_code}
        - CI Job: {project_code}/{module_code}/{app_code}-ci
        - CD Job: {project_code}/{module_code}/{app_code}-cd

        Args:
            project_code: 项目编码
            module_code: 模块编码
            app_code: 应用编码
            git_url: Git 仓库地址
            branch: 分支

        Returns:
            创建结果
        """
        results = {"ci": False, "cd": False}

        try:
            # 1. 创建项目目录
            if not self.create_folder(project_code):
                return results

            # 2. 创建模块目录
            if not self.create_folder(module_code, parent=project_code):
                return results

            folder = f"{project_code}/{module_code}"

            # 3. 创建 CI Job
            results["ci"] = self.create_pipeline_job(
                name=f"{app_code}-ci",
                folder=folder,
                git_url=git_url,
                branch=branch,
                jenkinsfile_path="Jenkinsfile",
                description=f"CI Pipeline for {project_code}/{module_code}/{app_code}"
            )

            # 4. 创建 CD Job
            results["cd"] = self.create_pipeline_job(
                name=f"{app_code}-cd",
                folder=folder,
                git_url=git_url,
                branch=branch,
                jenkinsfile_path="Jenkinsfile.deploy",
                description=f"CD Pipeline for {project_code}/{module_code}/{app_code}"
            )

        except DevOpsException as e:
            self._log_error(f"创建 CI/CD Jobs 失败: {e.message}")

        return results

    def get_job_full_name(self, project_code: str, module_code: str, app_code: str, job_type: str = "ci") -> str:
        """
        获取 Job 完整名称

        Args:
            project_code: 项目编码
            module_code: 模块编码
            app_code: 应用编码
            job_type: "ci" 或 "cd"

        Returns:
            Job 完整路径
        """
        return f"{project_code}/{module_code}/{app_code}-{job_type}"

    def test_connection(self) -> bool:
        """
        测试 Jenkins 连接

        Returns:
            连接是否成功
        """
        try:
            response = self._request("GET", "/api/json")
            if response.status_code == 200:
                self._log_info("Jenkins 连接测试成功")
                return True
            return False
        except DevOpsException as e:
            self._log_warning(f"Jenkins 连接测试失败: {e.message}")
            return False

    # ==================== 配置更新操作 ====================

    def get_job_config(self, name: str, folder: str = None) -> Optional[str]:
        """
        获取 Job 配置 XML

        Args:
            name: Job 名称
            folder: Folder 路径

        Returns:
            XML 配置字符串，失败返回 None
        """
        folder_path = self._build_job_path(folder) if folder else ""
        path = f"{folder_path}/job/{name}" if folder else f"/job/{name}"
        response = self._request("GET", f"{path}/config.xml")

        if response.status_code == 200:
            return response.text
        return None

    def update_job_config(
        self,
        name: str,
        folder: str = None,
        jenkinsfile_content: str = None,
        git_url: str = None,
        branch: str = "main",
        description: str = ""
    ) -> bool:
        """
        更新 Job 配置（用于同步 Jenkinsfile）

        Args:
            name: Job 名称
            folder: Folder 路径
            jenkinsfile_content: Jenkinsfile 内容（内联脚本模式）
            git_url: Git 仓库地址（可选，用于 SCM 模式）
            branch: 分支
            description: 描述

        Returns:
            是否更新成功
        """
        # 检查 Job 是否存在
        if not self.job_exists(name, folder):
            self._log_warning(f"Jenkins Job 不存在: {name}", {"folder": folder})
            # 自动创建
            return self.create_pipeline_job(
                name=name,
                folder=folder,
                git_url=git_url,
                branch=branch,
                description=description
            )

        # 生成新的配置 XML
        if jenkinsfile_content:
            # 使用内联脚本模式（直接使用 Jenkinsfile 内容）
            job_xml = self._generate_inline_pipeline_xml(
                script=jenkinsfile_content,
                description=description
            )
        else:
            # 使用 SCM 模式
            job_xml = self._generate_pipeline_xml(
                git_url=git_url,
                branch=branch,
                description=description
            )

        # 更新配置
        folder_path = self._build_job_path(folder) if folder else ""
        path = f"{folder_path}/job/{name}" if folder else f"/job/{name}"

        self._log_info(f"更新 Jenkins Job 配置: {name}", {"folder": folder})

        response = self._request("POST", f"{path}/config.xml", data=job_xml.encode("utf-8"))

        if response.status_code in [200, 201, 302]:
            self._log_info(f"Jenkins Job 配置更新成功: {name}")
            return True
        else:
            self._log_error(f"Jenkins Job 配置更新失败", {
                "status_code": response.status_code,
                "response": response.text[:500]
            })
            return False

    def _generate_inline_pipeline_xml(self, script: str, description: str = "") -> str:
        """生成内联脚本的 Pipeline Job XML 配置"""
        # 转义 XML 特殊字符
        escaped_script = script.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<flow-definition plugin="workflow-job">
  <description>{description}</description>
  <definition class="org.jenkinsci.plugins.workflow.cps.CpsFlowDefinition" plugin="workflow-cps">
    <script>{escaped_script}</script>
    <sandbox>true</sandbox>
  </definition>
  <triggers/>
  <disabled>false</disabled>
</flow-definition>'''

    def delete_job(self, name: str, folder: str = None) -> bool:
        """
        删除 Job

        Args:
            name: Job 名称
            folder: Folder 路径

        Returns:
            是否删除成功
        """
        folder_path = self._build_job_path(folder) if folder else ""
        path = f"{folder_path}/job/{name}" if folder else f"/job/{name}"

        self._log_info(f"删除 Jenkins Job: {name}", {"folder": folder})
        response = self._request("POST", f"{path}/doDelete")

        if response.status_code in [200, 302]:
            self._log_info(f"Jenkins Job 删除成功: {name}")
            return True
        return False

    def trigger_build(self, name: str, folder: str = None, parameters: Dict = None) -> bool:
        """
        触发构建

        Args:
            name: Job 名称
            folder: Folder 路径
            parameters: 构建参数

        Returns:
            是否触发成功
        """
        folder_path = self._build_job_path(folder) if folder else ""
        path = f"{folder_path}/job/{name}" if folder else f"/job/{name}"

        if parameters:
            # 参数化构建
            param_str = "&".join([f"{k}={v}" for k, v in parameters.items()])
            endpoint = f"{path}/buildWithParameters?{param_str}"
        else:
            endpoint = f"{path}/build"

        self._log_info(f"触发 Jenkins 构建: {name}", {"folder": folder, "parameters": parameters})
        response = self._request("POST", endpoint)

        if response.status_code in [200, 201, 302]:
            self._log_info(f"Jenkins 构建触发成功: {name}")
            return True
        return False
