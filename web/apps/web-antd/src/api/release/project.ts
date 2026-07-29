import { requestClient } from '#/api/request';

export namespace ReleaseProjectApi {
  export interface Project {
    id: number;
    name: string;
    code: string;
    description?: string;
    gitlab_group_id?: number;
    gitlab_group_url?: string;
    status: 0 | 1;
    sort: number;
    module_count?: number;
    app_count?: number;
    remark?: string;
    creator?: string;
    modifier?: string;
    create_time?: string;
    update_time?: string;
  }

  export interface ProjectListParams {
    page?: number;
    page_size?: number;
    name?: string;
    code?: string;
    status?: number;
  }

  export interface ProjectTree {
    id: number;
    name: string;
    code: string;
    modules: {
      id: number;
      name: string;
      code: string;
      applications: {
        id: number;
        name: string;
        code: string;
        app_type: string;
      }[];
    }[];
  }
}

/**
 * 获取项目列表
 */
async function getProjectList(params?: ReleaseProjectApi.ProjectListParams) {
  return requestClient.get<{ items: ReleaseProjectApi.Project[]; total: number }>('/release/project/', {
    params,
  });
}

/**
 * 获取项目详情
 */
async function getProjectDetail(id: number) {
  return requestClient.get<ReleaseProjectApi.Project>(`/release/project/${id}/`);
}

/**
 * 创建项目
 */
async function createProject(data: Partial<ReleaseProjectApi.Project>) {
  return requestClient.post<ReleaseProjectApi.Project>('/release/project/', data);
}

/**
 * 更新项目
 */
async function updateProject(id: number, data: Partial<ReleaseProjectApi.Project>) {
  return requestClient.put<ReleaseProjectApi.Project>(`/release/project/${id}/`, data);
}

/**
 * 删除项目
 */
async function deleteProject(id: number) {
  return requestClient.delete(`/release/project/${id}/`);
}

/**
 * 获取项目下的模块列表
 */
async function getProjectModules(id: number) {
  return requestClient.get(`/release/project/${id}/modules/`);
}

/**
 * 获取项目下的应用列表
 */
async function getProjectApplications(id: number) {
  return requestClient.get(`/release/project/${id}/applications/`);
}

/**
 * 获取项目树形结构
 */
async function getProjectTree() {
  return requestClient.get<ReleaseProjectApi.ProjectTree[]>('/release/project/tree/');
}

/**
 * 同步 GitLab Group
 */
async function syncProjectGitlab(id: number) {
  return requestClient.post(`/release/project/${id}/sync_gitlab/`);
}

/**
 * 获取项目同步日志
 */
async function getProjectSyncLogs(id: number) {
  return requestClient.get(`/release/project/${id}/sync_logs/`);
}

/**
 * 列出 GitLab Groups（用于导入）
 */
async function listGitLabGroups(params?: { search?: string; page?: number; per_page?: number }) {
  return requestClient.get('/release/project/list_gitlab_groups/', { params });
}

/**
 * 批量从 GitLab 导入 Groups
 */
async function importGitLabGroups(gitlabGroupIds: number[]) {
  return requestClient.post('/release/project/import_gitlab_groups/', { gitlab_group_ids: gitlabGroupIds });
}

/**
 * 从 GitLab 导入单个 Group
 */
async function importGitLabGroup(gitlabGroupId: number) {
  return requestClient.post('/release/project/import_gitlab_group/', { gitlab_group_id: gitlabGroupId });
}

/**
 * 列出 GitLab Projects（用于导入）
 */
async function listGitLabProjects(params?: { group_id?: number; search?: string; page?: number; per_page?: number }) {
  return requestClient.get('/release/project/list_gitlab_projects/', { params });
}

export {
  createProject,
  deleteProject,
  getProjectApplications,
  getProjectDetail,
  getProjectList,
  getProjectModules,
  getProjectSyncLogs,
  getProjectTree,
  syncProjectGitlab,
  updateProject,
  listGitLabGroups,
  importGitLabGroup,
  importGitLabGroups,
  listGitLabProjects,
};
