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
