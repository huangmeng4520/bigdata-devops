import { requestClient } from '#/api/request';

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
    page_size?: number;
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
 */
export function listGitLabProjects(params?: { group_id?: number; search?: string; page?: number; per_page?: number }) {
  return requestClient.get('/release/code-repository/list_gitlab_projects/', { params });
}

/**
 * 批量从 GitLab 导入 Projects
 */
export function importGitLabProjects(data: { gitlab_project_id: number; project_id?: number; module_id?: number }[]) {
  return requestClient.post('/release/code-repository/import_gitlab_projects/', { data });
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
