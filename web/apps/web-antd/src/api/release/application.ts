import { requestClient } from '#/api/request';

// 应用类型选项
export const APP_TYPE_OPTIONS = [
  { label: 'Java', value: 'java' },
  { label: 'Node.js', value: 'nodejs' },
  { label: 'Python', value: 'python' },
  { label: 'Go', value: 'go' },
  { label: 'Vue', value: 'vue' },
  { label: 'React', value: 'react' },
];

export namespace ReleaseApplicationApi {
  export interface Application {
    id: number;
    project: number;
    project_name?: string;
    module: number;
    module_name?: string;
    name: string;
    code: string;
    description?: string;
    app_type: string;
    app_type_display?: string;
    // 代码仓库关联
    code_repository?: number;
    code_repository_name?: string;
    code_repository_git_url?: string;
    code_subpath?: string;
    // 兼容旧字段
    git_url?: string;
    gitlab_project_id?: number;
    harbor_project?: string;
    build_branch: string;
    dockerfile_path: string;
    // Jenkins 同步状态
    jenkins_sync_status: 0 | 1 | 2 | 3;
    jenkins_sync_status_display?: string;
    jenkins_sync_time?: string;
    jenkins_sync_message?: string;
    // GitLab 同步状态
    gitlab_sync_status: 0 | 1 | 2 | 3;
    gitlab_sync_status_display?: string;
    gitlab_sync_time?: string;
    gitlab_sync_message?: string;
    // Harbor 同步状态
    harbor_sync_status: 0 | 1 | 2 | 3;
    harbor_sync_status_display?: string;
    harbor_sync_time?: string;
    harbor_sync_message?: string;
    status: 0 | 1;
    status_display?: string;
    sort: number;
    remark?: string;
    creator?: string;
    modifier?: string;
    create_time?: string;
    update_time?: string;
  }

  export interface ApplicationListParams {
    page?: number;
    pageSize?: number;
    name?: string;
    code?: string;
    project?: number;
    module?: number;
    code_repository?: number;
    app_type?: string;
    status?: number;
  }

  export interface JenkinsSyncStatus {
    sync_status: 0 | 1 | 2 | 3;
    sync_status_display: string;
    sync_time?: string;
    sync_message?: string;
  }

  export interface ResourceStatus {
    gitlab: {
      project_id?: number;
      git_url?: string;
      status: string;
      sync_status: number;
      sync_time?: string;
      sync_message?: string;
    };
    jenkins: {
      status: string;
      sync_status: number;
      sync_time?: string;
      sync_message?: string;
    };
    harbor: {
      project?: string;
      status: string;
      sync_status: number;
      sync_time?: string;
      sync_message?: string;
    };
  }

  export interface JenkinsfilePreview {
    content: string;
    template_name: string;
    template_version: string;
    variables: Record<string, any>;
    environment?: string;
  }
}

/**
 * 获取应用列表
 */
async function getApplicationList(params?: ReleaseApplicationApi.ApplicationListParams) {
  return requestClient.get<{ items: ReleaseApplicationApi.Application[]; total: number }>('/release/application/', {
    params,
  });
}

/**
 * 获取应用详情
 */
async function getApplicationDetail(id: number) {
  return requestClient.get<ReleaseApplicationApi.Application>(`/release/application/${id}/`);
}

/**
 * 创建应用
 */
async function createApplication(data: Partial<ReleaseApplicationApi.Application>) {
  return requestClient.post<ReleaseApplicationApi.Application>('/release/application/', data);
}

/**
 * 更新应用
 */
async function updateApplication(id: number, data: Partial<ReleaseApplicationApi.Application>) {
  return requestClient.put<ReleaseApplicationApi.Application>(`/release/application/${id}/`, data);
}

/**
 * 删除应用
 */
async function deleteApplication(id: number) {
  return requestClient.delete(`/release/application/${id}/`);
}

/**
 * 获取应用的配置包列表
 */
async function getApplicationConfigPackages(id: number) {
  return requestClient.get(`/release/application/${id}/config_packages/`);
}

/**
 * 获取应用的同步日志
 */
async function getApplicationSyncLogs(id: number) {
  return requestClient.get(`/release/application/${id}/sync_logs/`);
}

/**
 * 生成配置包
 */
async function generateConfig(id: number, version?: string) {
  return requestClient.post(`/release/application/${id}/generate_config/`, { version });
}

/**
 * 同步资源
 */
async function syncResources(id: number, type?: string, force?: boolean) {
  return requestClient.post(`/release/application/${id}/sync_resources/`, { type, force: force || false });
}

/**
 * 单独同步 GitLab 资源
 */
async function syncGitlab(id: number, force?: boolean) {
  return requestClient.post(`/release/application/${id}/sync_gitlab/`, { force: force || false });
}

/**
 * 单独同步 Harbor 资源
 */
async function syncHarbor(id: number, force?: boolean) {
  return requestClient.post(`/release/application/${id}/sync_harbor/`, { force: force || false });
}

/**
 * 获取资源状态
 */
async function getResourceStatus(id: number) {
  return requestClient.get<ReleaseApplicationApi.ResourceStatus>(`/release/application/${id}/resource_status/`);
}

/**
 * 同步 CI/CD 配置到 Jenkins
 */
async function syncApplicationToJenkins(id: number) {
  return requestClient.post<{ task_id: string; message: string }>(`/release/application/${id}/sync_to_jenkins/`);
}

/**
 * 获取 Jenkins 同步状态
 */
async function getJenkinsSyncStatus(id: number) {
  return requestClient.get<{ data: ReleaseApplicationApi.JenkinsSyncStatus }>(`/release/application/${id}/jenkins_sync_status/`);
}

/**
 * 预览 Jenkinsfile
 */
async function previewJenkinsfile(id: number, environment?: string) {
  return requestClient.get<{ data: ReleaseApplicationApi.JenkinsfilePreview }>(`/release/application/${id}/preview_jenkinsfile/`, {
    params: environment ? { environment } : {},
  });
}

export {
  createApplication,
  deleteApplication,
  generateConfig,
  getApplicationConfigPackages,
  getApplicationDetail,
  getApplicationList,
  getApplicationSyncLogs,
  getJenkinsSyncStatus,
  getResourceStatus,
  previewJenkinsfile,
  syncGitlab,
  syncHarbor,
  syncResources,
  syncApplicationToJenkins,
  updateApplication,
};
