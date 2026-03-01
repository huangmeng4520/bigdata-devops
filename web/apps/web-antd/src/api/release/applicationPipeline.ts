import { requestClient } from '#/api/request';

// 配置类型选项
export const CONFIG_TYPE_OPTIONS = [
  { label: 'CI 配置', value: 'ci' },
  { label: 'CD 配置', value: 'cd' },
];

// 环境选项
export const ENVIRONMENT_OPTIONS = [
  { label: '开发环境', value: 'dev' },
  { label: '测试环境', value: 'test' },
  { label: '准生产环境', value: 'staging' },
  { label: '生产环境', value: 'production' },
];

export namespace ApplicationPipelineApi {
  export interface ConfigVersion {
    id: number;
    config: number;
    config_name?: string;
    version: number;
    content: string;
    variables_snapshot: Record<string, any>;
    stages_snapshot: any[];
    generated_by: string;
    generated_by_name?: string;
    create_time?: string;
  }

  export interface Config {
    id: number;
    application: number;
    application_name?: string;
    config_type: 'ci' | 'cd';
    config_type_display?: string;
    environment: string;
    environment_display?: string;
    template?: number;
    template_name?: string;
    template_version?: number;
    template_version_name?: string;
    custom_content?: string;
    variables: Record<string, any>;
    stages_config: any[];
    is_active: boolean;
    current_version: number;
    version_count?: number;
    // Jenkins 同步状态
    jenkins_sync_status: 0 | 1 | 2 | 3;  // 0-待同步 1-同步中 2-已同步 3-同步失败
    jenkins_sync_status_display?: string;
    jenkins_sync_time?: string;
    jenkins_sync_message?: string;
    jenkins_job_name?: string;
    creator?: string;
    modifier?: string;
    create_time?: string;
    update_time?: string;
  }

  export interface ConfigListParams {
    page?: number;
    page_size?: number;
    application?: number;
    config_type?: string;
    environment?: string;
    template?: number;
    is_active?: boolean;
  }

  export interface SyncStatus {
    sync_status: 0 | 1 | 2 | 3;
    sync_status_display: string;
    sync_time?: string;
    sync_message?: string;
    jenkins_job_name?: string;
  }
}

/**
 * 获取配置列表
 */
async function getConfigList(params?: ApplicationPipelineApi.ConfigListParams) {
  return requestClient.get<{ items: ApplicationPipelineApi.Config[]; total: number }>('/release/application-pipeline-configs/', {
    params,
  });
}

/**
 * 获取配置详情
 */
async function getConfigDetail(id: number) {
  return requestClient.get<ApplicationPipelineApi.Config>(`/release/application-pipeline-configs/${id}/`);
}

/**
 * 创建配置
 */
async function createConfig(data: Partial<ApplicationPipelineApi.Config>) {
  return requestClient.post<ApplicationPipelineApi.Config>('/release/application-pipeline-configs/', data);
}

/**
 * 更新配置
 */
async function updateConfig(id: number, data: Partial<ApplicationPipelineApi.Config>) {
  return requestClient.put<ApplicationPipelineApi.Config>(`/release/application-pipeline-configs/${id}/`, data);
}

/**
 * 删除配置
 */
async function deleteConfig(id: number) {
  return requestClient.delete(`/release/application-pipeline-configs/${id}/`);
}

/**
 * 获取配置版本历史
 */
async function getConfigVersions(id: number, params?: { page?: number; page_size?: number }) {
  return requestClient.get<{ items: ApplicationPipelineApi.ConfigVersion[]; total: number }>(`/release/application-pipeline-configs/${id}/versions/`, {
    params,
  });
}

/**
 * 生成 Jenkinsfile
 */
async function generateJenkinsfile(id: number) {
  return requestClient.post<{ version: number; version_id: number; content: string }>(`/release/application-pipeline-configs/${id}/generate/`);
}

/**
 * 回滚配置
 */
async function rollbackConfig(id: number, targetVersion: number) {
  return requestClient.post(`/release/application-pipeline-configs/${id}/rollback/`, {
    target_version: targetVersion,
  });
}

/**
 * 同步配置到 Jenkins
 */
async function syncToJenkins(id: number) {
  return requestClient.post<{ task_id: string; message: string }>(`/release/application-pipeline-configs/${id}/sync_to_jenkins/`);
}

/**
 * 获取同步状态
 */
async function getSyncStatus(id: number) {
  return requestClient.get<{ data: ApplicationPipelineApi.SyncStatus }>(`/release/application-pipeline-configs/${id}/sync_status/`);
}

/**
 * 生成 Jenkinsfile 并同步到 Jenkins（一键操作）
 */
async function generateAndSync(id: number) {
  return requestClient.post<{
    version: number;
    version_id: number;
    content: string;
    task_id: string;
    message: string;
  }>(`/release/application-pipeline-configs/${id}/generate_and_sync/`);
}

// 配置版本相关 API
async function getVersionContent(id: number) {
  return requestClient.get<{ content: string; variables: Record<string, any>; stages: any[] }>(`/release/application-pipeline-versions/${id}/content/`);
}

// 命名验证 API
interface NamingValidationResult {
  valid: boolean;
  errors: { field: string; message: string; rule: string }[];
  suggestion?: string;
}

async function validateNaming(type: 'project' | 'module' | 'app', name: string) {
  return requestClient.post<NamingValidationResult>('/release/validate-naming/', {
    type,
    name,
  });
}

interface GeneratedNames {
  gitlab: {
    group: string;
    subgroup: string;
    repository: string;
  };
  harbor: {
    project: string;
    image: string;
    tag: string;
  };
  jenkins: {
    folder: string;
    job: string;
  };
  ansible: {
    inventory: string;
  };
}

async function generateNames(params: { project: string; module: string; app: string; version?: string; environment?: string }) {
  return requestClient.post<GeneratedNames>('/release/generate-names/', params);
}

export {
  createConfig,
  deleteConfig,
  generateAndSync,
  generateJenkinsfile,
  generateNames,
  getConfigDetail,
  getConfigList,
  getConfigVersions,
  getSyncStatus,
  getVersionContent,
  rollbackConfig,
  syncToJenkins,
  updateConfig,
  validateNaming,
};
