import type { Recordable } from '@vben/types';

import { requestClient } from '#/api/request';

export namespace ReleaseProjectApi {
  export interface Project {
    id: number;
    name: string;
    code: string;
    description?: string;
    gitlab_group_id?: number;
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
};
