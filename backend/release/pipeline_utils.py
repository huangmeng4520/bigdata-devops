# 应用字段自动注入的内置变量（模板中用 ${VAR} 引用，生成 Jenkinsfile 时替换）
# 优先级：应用字段注入 → 模板默认值 → 用户覆盖(config.variables)
BUILTIN_VARIABLES = [
    {'name': 'APP_NAME', 'source': 'app.name', 'desc': '应用名称'},
    {'name': 'APP_CODE', 'source': 'app.code', 'desc': '应用编码'},
    {'name': 'GIT_URL', 'source': 'app.git_url', 'desc': '应用 Git 地址'},
    {'name': 'GIT_REPO', 'source': 'code_repository.git_http_url 或 app.git_url', 'desc': '代码仓库地址（优先 code_repository）'},
    {'name': 'BUILD_BRANCH', 'source': 'app.build_branch（默认 main）', 'desc': '构建分支'},
    {'name': 'BUILD_COMMAND', 'source': 'app.build_command', 'desc': '构建命令'},
    {'name': 'CODE_SUBPATH', 'source': 'app.code_subpath', 'desc': '代码子路径'},
    {'name': 'DOCKERFILE_PATH', 'source': 'app.dockerfile_path（默认 ./Dockerfile）', 'desc': 'Dockerfile 路径'},
    {'name': 'PROJECT_NAME', 'source': 'app.project.code', 'desc': '项目编码'},
    {'name': 'MODULE_NAME', 'source': 'app.module.code', 'desc': '模块编码'},
]

# 应用发布时传给 Jenkins 的构建参数（命名与内置变量不同，模板内用 params.XXX 引用）
JENKINS_BUILD_PARAMS = [
    {'name': 'PROJECT', 'source': 'application.project.code', 'desc': '项目编码'},
    {'name': 'MODULE', 'source': 'application.module.code（无则 app.code）', 'desc': '模块编码'},
    {'name': 'APP', 'source': 'application.code', 'desc': '应用编码'},
    {'name': 'BRANCH', 'source': 'release.branch', 'desc': '发布分支'},
    {'name': 'VERSION', 'source': 'release.version（可空）', 'desc': '发布版本'},
    {'name': 'ENVIRONMENT', 'source': 'release.environment', 'desc': '目标环境'},
    {'name': 'GIT_REPO', 'source': 'code_repository.git_url 或 application.git_url', 'desc': '代码仓库地址'},
    {'name': 'CODE_SUBPATH', 'source': 'application.code_subpath', 'desc': '代码子路径'},
    {'name': 'BUILD_COMMAND', 'source': 'application.build_command', 'desc': '构建命令'},
    {'name': 'PACKAGE_NAME', 'source': '当前恒为空（未取值）', 'desc': '包名（预留）'},
]

# 触发构建前的必填校验项（任一缺失即 build_failed）
RELEASE_REQUIRED_FIELDS = [
    {'field': 'application.project.code', 'desc': '应用所属项目编码'},
    {'field': 'application.code', 'desc': '应用编码'},
    {'field': 'application.module.code', 'desc': '模块编码（无模块时回退为应用编码）'},
    {'field': 'release.branch', 'desc': '发布分支'},
    {'field': 'release.environment', 'desc': '目标环境'},
    {'field': 'git_url', 'desc': '代码仓库地址（code_repository.git_url 或 application.git_url）'},
    {'field': 'pipeline_config.jenkins_job_name', 'desc': '该环境已同步的 Jenkins Job 名（需先在流水线配置中同步）'},
]


def get_builtin_variables():
    """返回模板可用的内置变量清单（供前端展示提示）"""
    return BUILTIN_VARIABLES


def get_jenkins_build_params():
    """返回应用发布时传给 Jenkins 的构建参数清单（供前端展示提示）"""
    return JENKINS_BUILD_PARAMS


def get_release_required_fields():
    """返回触发构建前的必填校验项清单（供前端展示提示）"""
    return RELEASE_REQUIRED_FIELDS


def get_template_content(config):
    """获取模板内容及变量定义"""
    if config.template_version:
        return config.template_version.content, config.template_version.variables
    if config.template:
        latest_version = config.template.latest_version
        if latest_version:
            return latest_version.content, latest_version.variables
    return None, None


def build_pipeline_variables(app, config, template_variables_def=None):
    """构建流水线变量：应用字段注入 → 模板默认值 → 用户覆盖"""
    variables = {}

    variables['APP_NAME'] = app.name
    variables['APP_CODE'] = app.code
    variables['GIT_URL'] = app.git_url or ''

    git_repo = ''
    if hasattr(app, 'code_repository') and app.code_repository:
        git_repo = app.code_repository.git_http_url or ''
    if not git_repo and hasattr(app, 'code_repository') and app.code_repository:
        git_repo = app.code_repository.git_http_url or app.code_repository.git_url or ''
    if not git_repo:
        git_repo = app.git_url or ''
    variables['GIT_REPO'] = git_repo
    variables['BUILD_BRANCH'] = app.build_branch or 'main'
    variables['BUILD_COMMAND'] = app.build_command or ''
    variables['CODE_SUBPATH'] = app.code_subpath or ''
    variables['DOCKERFILE_PATH'] = app.dockerfile_path or './Dockerfile'
    if app.project_id:
        variables['PROJECT_NAME'] = app.project.code if hasattr(app, 'project') and app.project else ''
    if app.module_id:
        variables['MODULE_NAME'] = app.module.code if hasattr(app, 'module') and app.module else ''

    if template_variables_def and isinstance(template_variables_def, dict):
        for var in template_variables_def.get('variables', []):
            var_name = var.get('name')
            if var_name and var_name not in variables:
                variables[var_name] = var.get('default', '')

    if config and config.variables:
        variables.update(config.variables)

    return variables
