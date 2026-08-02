#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import xml.etree.ElementTree as ET
import json
import sys
from datetime import datetime
import os
import re
import errno
import logging

# ========== 配置区 ==========
JENKINS_URL = "http://your-jenkins-url"          # 修改为你的 Jenkins 地址
USERNAME = "your-username"
API_TOKEN = "your-api-token"
OUTPUT_ROOT = "./jenkins_jobs_export"
VERBOSE = True

DEFAULT_LANGUAGE = "java"
DEFAULT_LANGUAGE_VERSION = "17"
DEFAULT_FRAMEWORK = "springboot"
DEFAULT_VERSION = "1.0.3"
FETCH_FROM_SCM = False
# =============================

logging.basicConfig(level=logging.DEBUG if VERBOSE else logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class JenkinsAPI:
    def __init__(self, url, username, token):
        self.base_url = url.rstrip('/')
        self.auth = (username, token)
        self.session = requests.Session()
        self.session.auth = self.auth
        self.session.verify = False
        requests.packages.urllib3.disable_warnings()

    def get(self, endpoint, params=None):
        url = f"{self.base_url}{endpoint}"
        logger.debug(f"GET {url} params={params}")
        resp = self.session.get(url, params=params)
        logger.debug(f"Response status: {resp.status_code}")
        if resp.status_code != 200:
            logger.warning(f"Request failed: {resp.status_code} - {resp.text[:200]}")
        resp.raise_for_status()
        return resp

    def get_json(self, endpoint, params=None):
        resp = self.get(endpoint, params)
        return resp.json()

    def get_xml(self, endpoint, params=None):
        resp = self.get(endpoint, params)
        return resp.text


def normalize_git_url(raw_url):
    """
    将原始 Git URL 标准化为目标前缀。
    支持：
      - 以允许前缀开头且以 .git 结尾的地址 → 替换前缀为目标前缀
      - 包含 ${GIALAB_ADDRESS} 的地址 → 替换变量为目标前缀
      - 其他包含 .git 的地址尝试提取路径并拼接目标前缀
    """
    if not raw_url:
        return ""

    TARGET_PREFIX = "ssh://git@220.163.62.194:12002"

    # ---- 1) 处理包含变量 ${GIALAB_ADDRESS} 的情况 ----
    if "${GIALAB_ADDRESS}" in raw_url:
        new_url = raw_url.replace("${GIALAB_ADDRESS}", TARGET_PREFIX)
        logger.debug(f"替换变量 {raw_url} -> {new_url}")
        return new_url

    # ---- 2) 处理以允许前缀开头且以 .git 结尾的地址 ----
    allowed_prefixes = [
        "ssh://git@20.48.1.132:12002",
        "ssh://git@106.227.89.18:10093",
        "http://20.48.1.132:12001"
    ]

    for prefix in allowed_prefixes:
        if raw_url.startswith(prefix) and raw_url.endswith(".git"):
            suffix = raw_url[len(prefix):]
            if not suffix.startswith("/"):
                suffix = "/" + suffix
            new_url = TARGET_PREFIX + suffix
            logger.debug(f"URL 标准化: {raw_url} -> {new_url}")
            return new_url

    # ---- 3) 其他情况：尝试提取路径并拼接目标前缀 ----
    if ".git" in raw_url:
        match = re.search(r'://[^/]+(/.*\.git)', raw_url)
        if match:
            suffix = match.group(1)
            new_url = TARGET_PREFIX + suffix
            logger.debug(f"通用规则标准化: {raw_url} -> {new_url}")
            return new_url
        else:
            return raw_url
    else:
        return raw_url


def extract_pipeline_info(api, job_full_name):
    """
    从 config.xml 中提取 Pipeline 脚本内容和 Git 仓库 URL。
    返回 (script_content, scm_repo_url)
    """
    endpoint = f"/job/{job_full_name}/config.xml"
    try:
        xml_content = api.get_xml(endpoint)
    except Exception as e:
        return f"// 获取配置失败: {e}", ""

    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError:
        return "// 无法解析 config.xml", ""

    script_content = ""
    scm_url = ""

    definition = root.find("definition")
    if definition is None:
        return "// 未找到 definition 节点", ""

    def_class = definition.get("class", "")

    # ---- 处理直接脚本定义 ----
    if "CpsFlowDefinition" in def_class:
        script_node = definition.find("script")
        if script_node is not None and script_node.text:
            script_content = script_node.text.strip()
        else:
            script_content = "// script 节点为空"
        scm_url = extract_git_url_from_script(script_content)

    # ---- 处理 SCM 定义 ----
    elif "CpsScmFlowDefinition" in def_class:
        scm_node = definition.find("scm")
        if scm_node is not None:
            # 1) 直接 <url> 节点
            for url_node in scm_node.findall(".//url"):
                if url_node.text:
                    scm_url = url_node.text
                    break
            # 2) 从 <userRemoteConfigs> 中找
            if not scm_url:
                for user_remote in scm_node.findall(".//userRemoteConfigs//userRemoteConfig"):
                    url_node = user_remote.find("url")
                    if url_node is not None and url_node.text:
                        scm_url = url_node.text
                        break
            # 3) 从 <repositoryUrl> 中找
            if not scm_url:
                for repo_node in scm_node.findall(".//repositoryUrl"):
                    if repo_node.text:
                        scm_url = repo_node.text
                        break

            if scm_url:
                scm_url = normalize_git_url(scm_url)

        script_path_node = definition.find("scriptPath")
        script_path = script_path_node.text if script_path_node is not None else "Jenkinsfile"
        script_content = f"// Pipeline from SCM: {script_path}\n// URL: {scm_url}"

    else:
        script_content = f"// 未知 definition 类型: {def_class}"

    # ---- 兜底：如果 scm_url 仍为空，从脚本内容再提取 ----
    if not scm_url and script_content:
        scm_url = extract_git_url_from_script(script_content)

    return script_content, scm_url


def extract_git_url_from_script(script):
    """
    从 Pipeline 脚本内容中提取 Git URL（支持多种写法）。
    """
    if not script:
        return ""

    patterns = [
        r"git\s+url\s*:\s*['\"]([^'\"]+?)['\"]",
        r"checkout\s*\(.*?url\s*:\s*['\"]([^'\"]+?)['\"]",
        r"userRemoteConfigs\s*:\s*\[.*?url\s*:\s*['\"]([^'\"]+?)['\"]",
        r"git\s+clone\s+['\"]([^'\"]+?\.git)['\"]",
        r"(git@[\w.-]+:\S+?\.git)",
        r"(https?://[^'\"]+?\.git)",
    ]

    for pattern in patterns:
        matches = re.findall(pattern, script, re.IGNORECASE | re.DOTALL)
        if matches:
            raw_url = matches[0].strip()
            if raw_url and ("://" in raw_url or raw_url.startswith("git@") or "${" in raw_url):
                logger.debug(f"从脚本中提取到 URL: {raw_url}")
                return normalize_git_url(raw_url)
    return ""


def get_all_jobs(api, parent_path=""):
    jobs = []
    if parent_path:
        endpoint = f"/job/{parent_path}/api/json?tree=jobs[name,url,_class]"
    else:
        endpoint = "/api/json?tree=jobs[name,url,_class]"

    try:
        data = api.get_json(endpoint)
    except Exception as e:
        logger.error(f"获取 {parent_path or '根'} 下的 Job 列表失败: {e}")
        return jobs

    job_list = data.get("jobs", [])
    logger.debug(f"在 {parent_path or '根'} 下找到 {len(job_list)} 个条目")

    for job in job_list:
        name = job["name"]
        full_name = f"{parent_path}/{name}" if parent_path else name
        job_class = job.get("_class", "")
        logger.debug(f"  Job: {full_name}, _class: {job_class}")

        if "WorkflowJob" in job_class:
            jobs.append((full_name, "pipeline"))
        elif "WorkflowMultiBranchProject" in job_class:
            logger.info(f"发现多分支流水线: {full_name}，正在获取其分支...")
            try:
                branch_endpoint = f"/job/{full_name}/api/json?tree=jobs[name,url,_class]"
                branch_data = api.get_json(branch_endpoint)
                for branch_job in branch_data.get("jobs", []):
                    branch_name = branch_job["name"]
                    branch_full = f"{full_name}/{branch_name}"
                    if "WorkflowJob" in branch_job.get("_class", ""):
                        jobs.append((branch_full, "pipeline"))
                    else:
                        logger.debug(f"  分支 {branch_full} 类型非 WorkflowJob，忽略: {branch_job.get('_class')}")
            except Exception as e:
                logger.error(f"获取多分支 {full_name} 的子 Job 失败: {e}")
        elif "Folder" in job_class:
            logger.debug(f"进入文件夹: {full_name}")
            jobs.extend(get_all_jobs(api, full_name))
        elif "OrganizationFolder" in job_class:
            logger.info(f"发现组织文件夹: {full_name}，尝试递归...")
            jobs.extend(get_all_jobs(api, full_name))
        else:
            logger.debug(f"忽略非 Pipeline Job: {full_name} ({job_class})")

    return jobs


def safe_filename(name):
    safe = re.sub(r'[^a-zA-Z0-9_\-./]', '_', name)
    parts = safe.split('/')
    parts = [p for p in parts if p not in ('..', '.')]
    return '/'.join(parts)


def ensure_dir(path):
    try:
        os.makedirs(path, exist_ok=True)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise


def main():
    api = JenkinsAPI(JENKINS_URL, USERNAME, API_TOKEN)

    try:
        version_info = api.get_json("/api/json?tree=version")
        logger.info(f"Jenkins 版本: {version_info.get('version', '未知')}")
    except Exception as e:
        logger.error(f"连接 Jenkins 失败: {e}")
        sys.exit(1)

    logger.info("开始获取所有 Job...")
    all_jobs = get_all_jobs(api)
    pipeline_jobs = [(name, typ) for name, typ in all_jobs if typ == "pipeline"]
    logger.info(f"共找到 {len(all_jobs)} 个 Job，其中 Pipeline Job: {len(pipeline_jobs)} 个")

    if not pipeline_jobs:
        logger.warning("没有找到任何 Pipeline Job，请检查 Jenkins 中是否有流水线项目，或检查权限。")
        return

    ensure_dir(OUTPUT_ROOT)
    success_count = 0

    for idx, (full_name, _) in enumerate(pipeline_jobs, 1):
        logger.info(f"处理 [{idx}/{len(pipeline_jobs)}]: {full_name}")

        try:
            meta = api.get_json(f"/job/{full_name}/api/json")
            description = meta.get("description", "")
        except Exception as e:
            logger.error(f"获取 {full_name} 元数据失败: {e}")
            description = f"获取描述失败: {e}"

        if not description:
            description = datetime.now().strftime("%Y%m%d")

        script_content, git_url = extract_pipeline_info(api, full_name)

        template = {
            "name": full_name,
            "code": full_name,
            "language": DEFAULT_LANGUAGE,
            "language_version": DEFAULT_LANGUAGE_VERSION,
            "framework": DEFAULT_FRAMEWORK,
            "description": description,
            "git_url": git_url
        }

        version = {
            "version": DEFAULT_VERSION,
            "content": script_content,
            "variables": {},
            "stages": [],
            "stages_content": {}
        }

        entry = {
            "template": template,
            "version": version
        }

        rel_path = safe_filename(full_name) + ".json"
        out_path = os.path.join(OUTPUT_ROOT, rel_path)
        ensure_dir(os.path.dirname(out_path))

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(entry, f, ensure_ascii=False, indent=2)

        success_count += 1

    logger.info(f"完成！成功导出 {success_count} 个 Job")
    logger.info(f"文件保存在：{OUTPUT_ROOT}")


if __name__ == "__main__":
    main()

#     dry-run 验证完美通过：匹配的 job 成功匹配到 CodeRepository（repo id=409, project=大前端, module=数据条线），未匹配的 job 正确进入未匹配列表。现在清理测试文件并完成任务4。
# 所有任务已完成，更新计划状态为已完成：
# 所有任务已全部完成。以下是本次工作的总结：

# ## 完成内容

# ### 1. 扩展字段长度（已完成）
# - `backend/release/models.py`：`Application.code` 和 `Application.name` 从 max_length=32/64 扩展到 128，以容纳长 Jenkins job name
# - `backend/release/migrations/0023_alter_application_code_length.py`：自动生成的迁移文件，已应用到数据库

# ### 2. 创建导入脚本（已完成）
# - `backend/release/management/commands/import_jenkins_jobs.py`：Django management command
# - **核心流程**：读取用户脚本导出的 JSON 目录 → 通过 `git_url` 反查 `CodeRepository`（三级匹配策略：git_http_url 精确匹配 → git_url 精确匹配 → 路径部分匹配）→ 自动获取关联的 project 和 module → 创建 `Application` + `PipelineTemplate` + `PipelineTemplateVersion` + `ApplicationPipelineConfig`
# - **关键特性**：
#   - `jenkins_job_name` 保存原始 job 全路径，`jenkins_sync_status=2`（已同步），`config_dirty=False`
#   - 支持 `--dry-run` 预检匹配结果，输出匹配/未匹配报告
#   - 支持 `--dir`、`--environment`、`--app-type`、`--build-branch`、`--force` 参数
#   - 支持 `--skip-existing`（默认启用）跳过已存在的 Application

# ### 3. 修改同步逻辑（已完成）
# 修改了 `backend/release/tasks.py` 中 3 处同步逻辑：

# | 函数 | 行号 | 修改内容 |
# |------|------|----------|
# | `sync_jenkins_config` | 552-566 | 已导入旧 job（有 `jenkins_job_name`）按原始路径同步，新建用系统命名规则 |
# | `_sync_pipeline_config` | 633-647 | 同上逻辑 |
# | `create_jenkins_resources` | 157-167 | **额外发现的遗漏点**：已导入旧 job 的 config 跳过创建，避免在 Jenkins 上创建重复 job |

# ### 4. 验证（已完成）
# - **code-explorer 调用链分析**：确认 `update_job_config` 和 `_sync_pipeline_config` 的所有调用点都已覆盖；`trigger_jenkins_build` 及其下游（`poll_build_status`、`fetch_build_log`）完全兼容新逻辑；Views 层无直接同步代码
# - **dry-run 验证**：用真实 `CodeRepository` 数据构造测试 JSON，验证匹配逻辑正确工作（匹配成功/未匹配都能正确分类）

# ## 使用方式

# ```bash
# # 1. 先用用户脚本导出 Jenkins job 为 JSON
# python docs/jenkinsjob-json.py  # 导出到 ./jenkins_jobs_export/

# # 2. 预检匹配结果
# cd backend
# python manage.py import_jenkins_jobs --dir ../jenkins_jobs_export --dry-run

# # 3. 确认无误后正式导入
# python manage.py import_jenkins_jobs --dir ../jenkins_jobs_export --environment test
# ```