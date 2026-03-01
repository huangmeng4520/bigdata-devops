import { requestClient } from '#/api/request';

// 模板类型选项
export const TEMPLATE_TYPE_OPTIONS = [
  { label: 'CI 模板', value: 'ci' },
  { label: 'CD 模板', value: 'cd' },
];

// 语言选项
export const LANGUAGE_OPTIONS = [
  { label: 'Java', value: 'java' },
  { label: 'Python', value: 'python' },
  { label: 'Node.js', value: 'nodejs' },
  { label: 'Go', value: 'go' },
  { label: '.NET', value: 'dotnet' },
];

export namespace PipelineTemplateApi {
  export interface TemplateVersion {
    id: number;
    template: number;
    template_name?: string;
    version: string;
    content: string;
    variables: Record<string, any>;
    stages: any[];
    stages_content: Record<string, string>;
    change_log?: string;
    is_latest: boolean;
    status: number;
    status_display?: string;
    creator?: string;
    create_time?: string;
  }

  export interface Template {
    id: number;
    name: string;
    code: string;
    template_type: 'ci' | 'cd';
    template_type_display?: string;
    language: string;
    language_version?: string;
    framework?: string;
    description?: string;
    is_official: boolean;
    status: number;
    status_display?: string;
    version_count?: number;
    latest_version?: { id: number; version: string } | null;
    versions?: TemplateVersion[];
    creator?: string;
    modifier?: string;
    create_time?: string;
    update_time?: string;
  }

  export interface TemplateListParams {
    page?: number;
    page_size?: number;
    name?: string;
    code?: string;
    template_type?: string;
    language?: string;
    framework?: string;
    is_official?: boolean;
    status?: number;
  }

  export interface VersionListParams {
    page?: number;
    page_size?: number;
    template?: number;
    is_latest?: boolean;
    status?: number;
  }

  export interface ExportData {
    template: Partial<Template>;
    version: Partial<TemplateVersion> | null;
  }
}

/**
 * 获取模板列表
 */
async function getTemplateList(params?: PipelineTemplateApi.TemplateListParams) {
  return requestClient.get<{ items: PipelineTemplateApi.Template[]; total: number }>('/release/pipeline-templates/', {
    params,
  });
}

/**
 * 获取模板详情
 */
async function getTemplateDetail(id: number) {
  return requestClient.get<PipelineTemplateApi.Template>(`/release/pipeline-templates/${id}/`);
}

/**
 * 创建模板
 */
async function createTemplate(data: Partial<PipelineTemplateApi.Template>) {
  return requestClient.post<PipelineTemplateApi.Template>('/release/pipeline-templates/', data);
}

/**
 * 更新模板
 */
async function updateTemplate(id: number, data: Partial<PipelineTemplateApi.Template>) {
  return requestClient.put<PipelineTemplateApi.Template>(`/release/pipeline-templates/${id}/`, data);
}

/**
 * 删除模板
 */
async function deleteTemplate(id: number) {
  return requestClient.delete(`/release/pipeline-templates/${id}/`);
}

/**
 * 获取模板版本列表
 */
async function getTemplateVersions(id: number, params?: PipelineTemplateApi.VersionListParams) {
  return requestClient.get<{ items: PipelineTemplateApi.TemplateVersion[]; total: number }>(`/release/pipeline-templates/${id}/versions/`, {
    params,
  });
}

/**
 * 创建模板版本
 */
async function createTemplateVersion(id: number, data: Partial<PipelineTemplateApi.TemplateVersion>) {
  return requestClient.post<PipelineTemplateApi.TemplateVersion>(`/release/pipeline-templates/${id}/create_version/`, data);
}

/**
 * 预览 Jenkinsfile
 */
async function previewTemplate(id: number, data: { variables?: Record<string, any>; stages_config?: any[]; version_id?: number }) {
  return requestClient.post<{ content: string; variables: Record<string, any>; stages: any[] }>(`/release/pipeline-templates/${id}/preview/`, data);
}

// 模板版本相关 API
async function getVersionList(params?: PipelineTemplateApi.VersionListParams) {
  return requestClient.get<{ items: PipelineTemplateApi.TemplateVersion[]; total: number }>('/release/pipeline-template-versions/', {
    params,
  });
}

async function getVersionDetail(id: number) {
  return requestClient.get<PipelineTemplateApi.TemplateVersion>(`/release/pipeline-template-versions/${id}/`);
}

async function setLatestVersion(id: number) {
  return requestClient.post(`/release/pipeline-template-versions/${id}/set_latest/`);
}

async function copyTemplate(id: number, data: { name: string; code: string }) {
  return requestClient.post<{ id: number }>(`/release/pipeline-templates/${id}/copy/`, data);
}

async function exportTemplate(id: number) {
  return requestClient.get<PipelineTemplateApi.ExportData>(`/release/pipeline-templates/${id}/export_config/`);
}

async function importTemplate(data: PipelineTemplateApi.ExportData) {
  return requestClient.post<{ id: number }>('/release/pipeline-templates/import_config/', data);
}

async function autoVersionIncrement(versionId: number, changeLog?: string) {
  return requestClient.post<PipelineTemplateApi.TemplateVersion>(`/release/pipeline-template-versions/${versionId}/auto_version/`, { change_log: changeLog });
}

async function updateStage(versionId: number, stageName: string, stageScript: string) {
  return requestClient.put(`/release/pipeline-template-versions/${versionId}/update_stage/`, { stage_name: stageName, stage_script: stageScript });
}

async function updateVersionContent(versionId: number, content: string) {
  return requestClient.put(`/release/pipeline-template-versions/${versionId}/`, { content });
}

async function updateVersion(versionId: number, data: { version?: string; content?: string; change_log?: string }) {
  return requestClient.put(`/release/pipeline-template-versions/${versionId}/`, data);
}

export {
  autoVersionIncrement,
  copyTemplate,
  createTemplate,
  createTemplateVersion,
  deleteTemplate,
  exportTemplate,
  getTemplateDetail,
  getTemplateList,
  getTemplateVersions,
  getVersionDetail,
  getVersionList,
  importTemplate,
  previewTemplate,
  setLatestVersion,
  updateStage,
  updateTemplate,
  updateVersion,
  updateVersionContent,
};
