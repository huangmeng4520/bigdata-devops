/**
 * 流水线模板/应用发布相关的硬性逻辑提示常量
 *
 * 与后端 backend/release/pipeline_utils.py 中的
 * BUILTIN_VARIABLES / JENKINS_BUILD_PARAMS / RELEASE_REQUIRED_FIELDS 保持一致，
 * 供前端页面直接渲染提示，避免用户踩坑。
 */

/** 变量替换优先级说明（生成 Jenkinsfile 时变量合并顺序） */
export const VARIABLE_PRIORITY = [
  '① 应用字段自动注入（硬编码，如 APP_NAME / GIT_REPO）',
  '② 模板默认值（模板 variables 定义中的 default）',
  '③ 用户覆盖（config.variables，优先级最高）',
];

/** 模板可用的内置变量清单（模板中用 ${VAR} 引用，生成 Jenkinsfile 时替换） */
export const BUILTIN_VARIABLES = [
  { name: 'APP_NAME', source: 'app.name', desc: '应用名称' },
  { name: 'APP_CODE', source: 'app.code', desc: '应用编码' },
  { name: 'GIT_URL', source: 'app.git_url', desc: '应用 Git 地址' },
  {
    name: 'GIT_REPO',
    source: 'code_repository.git_http_url 或 app.git_url',
    desc: '代码仓库地址（优先 code_repository）',
  },
  {
    name: 'BUILD_BRANCH',
    source: 'app.build_branch（默认 main）',
    desc: '构建分支',
  },
  { name: 'BUILD_COMMAND', source: 'app.build_command', desc: '构建命令' },
  { name: 'CODE_SUBPATH', source: 'app.code_subpath', desc: '代码子路径' },
  {
    name: 'DOCKERFILE_PATH',
    source: 'app.dockerfile_path（默认 ./Dockerfile）',
    desc: 'Dockerfile 路径',
  },
  { name: 'PROJECT_NAME', source: 'app.project.code', desc: '项目编码' },
  { name: 'MODULE_NAME', source: 'app.module.code', desc: '模块编码' },
];

/** 应用发布时传给 Jenkins 的构建参数（模板内用 params.XXX 引用） */
export const JENKINS_BUILD_PARAMS = [
  { name: 'PROJECT', source: 'application.project.code', desc: '项目编码' },
  {
    name: 'MODULE',
    source: 'application.module.code（无则 app.code）',
    desc: '模块编码',
  },
  { name: 'APP', source: 'application.code', desc: '应用编码' },
  { name: 'BRANCH', source: 'release.branch', desc: '发布分支' },
  {
    name: 'VERSION',
    source: 'release.version（可空）',
    desc: '发布版本',
  },
  { name: 'ENVIRONMENT', source: 'release.environment', desc: '目标环境' },
  {
    name: 'GIT_REPO',
    source: 'code_repository.git_url 或 application.git_url',
    desc: '代码仓库地址',
  },
  {
    name: 'CODE_SUBPATH',
    source: 'application.code_subpath',
    desc: '代码子路径',
  },
  {
    name: 'BUILD_COMMAND',
    source: 'application.build_command',
    desc: '构建命令',
  },
  {
    name: 'PACKAGE_NAME',
    source: '当前恒为空（未取值）',
    desc: '包名（预留）',
  },
];

/** 触发构建前的必填校验项（任一缺失即 build_failed） */
export const RELEASE_REQUIRED_FIELDS = [
  { field: 'application.project.code', desc: '应用所属项目编码' },
  { field: 'application.code', desc: '应用编码' },
  {
    field: 'application.module.code',
    desc: '模块编码（无模块时回退为应用编码）',
  },
  { field: 'release.branch', desc: '发布分支' },
  { field: 'release.environment', desc: '目标环境' },
  {
    field: 'git_url',
    desc: '代码仓库地址（code_repository.git_url 或 application.git_url）',
  },
  {
    field: 'pipeline_config.jenkins_job_name',
    desc: '该环境已同步的 Jenkins Job 名（需先在流水线配置中同步）',
  },
];

/** 内置变量表格列定义（供 a-table 直接使用） */
export const BUILTIN_VAR_COLUMNS = [
  { title: '变量', dataIndex: 'name', width: 160 },
  { title: '来源', dataIndex: 'source' },
  { title: '说明', dataIndex: 'desc', width: 200 },
];

/** Jenkins 构建参数表格列定义 */
export const BUILD_PARAM_COLUMNS = [
  { title: '参数', dataIndex: 'name', width: 140 },
  { title: '来源', dataIndex: 'source' },
  { title: '说明', dataIndex: 'desc', width: 180 },
];
