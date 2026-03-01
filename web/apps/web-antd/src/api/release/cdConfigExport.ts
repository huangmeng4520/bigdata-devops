import { requestClient } from '#/api/request';

// 导出格式选项
export const EXPORT_FORMAT_OPTIONS = [
  { label: 'Jenkinsfile', value: 'jenkinsfile' },
  { label: 'JSON 配置', value: 'json' },
  { label: 'YAML 配置', value: 'yaml' },
  { label: '压缩包', value: 'zip' },
];

export namespace CDConfigExportApi {
  export interface Export {
    id: number;
    application: number;
    application_name?: string;
    environment: string;
    config_version: number;
    export_format: 'jenkinsfile' | 'json' | 'yaml' | 'zip';
    export_format_display?: string;
    content: string;
    file_path?: string;
    exported_by: string;
    exported_by_name?: string;
    download_count: number;
    create_time?: string;
  }

  export interface ExportListParams {
    page?: number;
    page_size?: number;
    application?: number;
    environment?: string;
    config_version?: number;
    export_format?: string;
    exported_by?: string;
  }
}

/**
 * 获取导出列表
 */
async function getExportList(params?: CDConfigExportApi.ExportListParams) {
  return requestClient.get<{ items: CDConfigExportApi.Export[]; total: number }>('/release/cd-exports/', {
    params,
  });
}

/**
 * 获取导出详情
 */
async function getExportDetail(id: number) {
  return requestClient.get<CDConfigExportApi.Export>(`/release/cd-exports/${id}/`);
}

/**
 * 创建导出
 */
async function createExport(data: Partial<CDConfigExportApi.Export>) {
  return requestClient.post<CDConfigExportApi.Export>('/release/cd-exports/', data);
}

/**
 * 删除导出
 */
async function deleteExport(id: number) {
  return requestClient.delete(`/release/cd-exports/${id}/`);
}

/**
 * 下载导出
 */
async function downloadExport(id: number) {
  return requestClient.post<{ content: string; format: string; filename: string }>(`/release/cd-exports/${id}/download/`);
}

/**
 * 获取 Jenkinsfile 内容
 */
async function getExportJenkinsfile(id: number) {
  return requestClient.get<{ content: string }>(`/release/cd-exports/${id}/jenkinsfile/`);
}

/**
 * 获取 JSON 配置
 */
async function getExportJson(id: number) {
  return requestClient.get<{ content: string }>(`/release/cd-exports/${id}/json_config/`);
}

export {
  createExport,
  deleteExport,
  downloadExport,
  getExportDetail,
  getExportJenkinsfile,
  getExportJson,
  getExportList,
};
