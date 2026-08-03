import { requestClient, baseRequestClient } from '#/api/request';
import { useAccessStore } from '@vben/stores';
import { formatToken } from '#/utils/auth';

export const REPOSITORY_TYPE_OPTIONS = [
  { label: 'GitLab', value: 'gitlab' },
  { label: 'GitHub', value: 'github' },
  { label: 'Gitee', value: 'gitee' },
];

export namespace CodeRepositoryApi {
  export interface CodeRepository {
    id: number;
    project: number;
    project_name?: string;
    module?: number;
    module_name?: string;
    name: string;
    code: string;
    repository_type: string;
    repository_type_display?: string;
    gitlab_project_id?: number;
    git_url: string;
    git_http_url?: string;
    app_count?: number;
    code_subpath?: string;
    build_command?: string;
    package_name?: string;
    default_branch: string;
    status: 0 | 1;
    status_display?: string;
    description?: string;
    creator?: string;
    create_time?: string;
    update_time?: string;
  }

  export interface CodeRepositoryListParams {
    page?: number;
    pageSize?: number;
    name?: string;
    code?: string;
    project?: number;
    module?: number;
    repository_type?: string;
    status?: number;
  }
}

export function getCodeRepositoryList(params?: CodeRepositoryApi.CodeRepositoryListParams) {
  return requestClient.get<{ items: CodeRepositoryApi.CodeRepository[]; total: number }>('/release/code-repository/', {
    params,
  });
}

export function getCodeRepositoryDetail(id: number) {
  return requestClient.get<CodeRepositoryApi.CodeRepository>(`/release/code-repository/${id}/`);
}

export function createCodeRepository(data: Partial<CodeRepositoryApi.CodeRepository>) {
  return requestClient.post<CodeRepositoryApi.CodeRepository>('/release/code-repository/', data);
}

export function updateCodeRepository(id: number, data: Partial<CodeRepositoryApi.CodeRepository>) {
  return requestClient.put<CodeRepositoryApi.CodeRepository>(`/release/code-repository/${id}/`, data);
}

export function deleteCodeRepository(id: number) {
  return requestClient.delete(`/release/code-repository/${id}/`);
}

export function syncGitlab(id: number) {
  return requestClient.post(`/release/code-repository/${id}/sync_gitlab/`);
}

/**
 * 列出 GitLab Projects（用于导入）
 * 使用 baseRequestClient 获取完整响应，手动解析避免 interceptor 干扰
 * 返回结构: { projects: [], total: number, imported_ids: number[] }
 */
export async function listGitLabProjects(params?: { group_id?: number; search?: string; page?: number; per_page?: number }) {
  const accessStore = useAccessStore();
  const resp = await baseRequestClient.get('/release/code-repository/list_gitlab_projects/', {
    params,
    headers: { Authorization: formatToken(accessStore.accessToken) },
  });
  // baseRequestClient 返回原始 axios 响应: resp.data = { code: 0, data: { projects, total, imported_ids } }
  const body = resp?.data || resp || {};
  const inner = body?.data || body;
  return {
    projects: inner?.projects || [],
    total: inner?.total || 0,
    imported_ids: inner?.imported_ids || [],
  };
}

/**
 * 批量从 GitLab 导入 Projects（异步任务，后端改为 Celery 处理，快速返回 task_id）
 */
export async function importGitLabProjects(data: { gitlab_project_id: number; project_id?: number; module_id?: number }[]) {
  const accessStore = useAccessStore();
  const resp = await baseRequestClient.post(
    '/release/code-repository/import_gitlab_projects/',
    { data },
    {
      headers: { Authorization: formatToken(accessStore.accessToken) },
      timeout: 300_000,  // 5 分钟兜底超时（后端已异步，实际秒级返回）
    },
  );
  // resp.data = { code, message, data: { task_id, total, ... } }
  const body = resp?.data || resp || {};
  return {
    message: body?.message || '',
    ...(body?.data || body),
  };
}

/**
 * 从 GitLab 导入单个 Project
 */
export function importGitLabProject(gitlabProjectId: number, projectId?: number, moduleId?: number) {
  return requestClient.post('/release/code-repository/import_gitlab_project/', { 
    gitlab_project_id: gitlabProjectId,
    project_id: projectId,
    module_id: moduleId
  });
}
