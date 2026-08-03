import { requestClient } from '#/api/request';

export namespace ReleaseModuleApi {
  export interface Module {
    id: number;
    project: number;
    project_name?: string;
    name: string;
    code: string;
    description?: string;
    gitlab_subgroup_id?: number;
    gitlab_subgroup_url?: string;
    status: 0 | 1;
    sort: number;
    app_count?: number;
    repo_count?: number;
    remark?: string;
    creator?: string;
    modifier?: string;
    create_time?: string;
    update_time?: string;
  }

  export interface ModuleListParams {
    page?: number;
    pageSize?: number;
    name?: string;
    code?: string;
    project?: number;
    status?: number;
  }
}

/**
 * 获取模块列表
 */
async function getModuleList(params?: ReleaseModuleApi.ModuleListParams) {
  return requestClient.get<{ items: ReleaseModuleApi.Module[]; total: number }>('/release/module/', {
    params,
  });
}

/**
 * 获取模块详情
 */
async function getModuleDetail(id: number) {
  return requestClient.get<ReleaseModuleApi.Module>(`/release/module/${id}/`);
}

/**
 * 创建模块
 */
async function createModule(data: Partial<ReleaseModuleApi.Module>) {
  return requestClient.post<ReleaseModuleApi.Module>('/release/module/', data);
}

/**
 * 更新模块
 */
async function updateModule(id: number, data: Partial<ReleaseModuleApi.Module>) {
  return requestClient.put<ReleaseModuleApi.Module>(`/release/module/${id}/`, data);
}

/**
 * 删除模块
 */
async function deleteModule(id: number) {
  return requestClient.delete(`/release/module/${id}/`);
}

/**
 * 获取模块下的应用列表
 */
async function getModuleApplications(id: number) {
  return requestClient.get(`/release/module/${id}/applications/`);
}

/**
 * 按项目获取模块列表
 */
async function getModulesByProject(projectId: number) {
  return requestClient.get('/release/module/by_project/', {
    params: { project_id: projectId },
  });
}

/**
 * 同步 GitLab Subgroup
 */
async function syncModuleGitlab(id: number) {
  return requestClient.post(`/release/module/${id}/sync_gitlab/`);
}

/**
 * 获取模块同步日志
 */
async function getModuleSyncLogs(id: number) {
  return requestClient.get(`/release/module/${id}/sync_logs/`);
}

/**
 * 列出 GitLab Subgroups（用于导入）
 */
async function listGitLabSubgroups(params: { parent_id: number; page?: number; per_page?: number }) {
  return requestClient.get('/release/module/list_gitlab_subgroups/', { params });
}

/**
 * 批量从 GitLab 导入 Subgroups
 */
async function importGitLabSubgroups(data: { gitlab_subgroup_id: number; project_id: number }[]) {
  return requestClient.post('/release/module/import_gitlab_subgroups/', { data });
}

/**
 * 从 GitLab 导入单个 Subgroup
 */
async function importGitLabSubgroup(gitlabSubgroupId: number, projectId: number) {
  return requestClient.post('/release/module/import_gitlab_subgroup/', { 
    gitlab_subgroup_id: gitlabSubgroupId,
    project_id: projectId 
  });
}

export {
  createModule,
  deleteModule,
  getModuleApplications,
  getModuleDetail,
  getModuleList,
  getModuleSyncLogs,
  getModulesByProject,
  syncModuleGitlab,
  updateModule,
  listGitLabSubgroups,
  importGitLabSubgroup,
  importGitLabSubgroups,
};
