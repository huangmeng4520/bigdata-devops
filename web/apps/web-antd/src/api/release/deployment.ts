/**
 * 发布管理 API
 */
import { requestClient } from '#/api/request';

// ============================================================
// 发布记录 API
// ============================================================

/** 发布记录列表 */
export function getReleaseList(params?: any) {
  return requestClient.get('/release/release-records/', { params });
}

/** 发布记录详情 */
export function getReleaseDetail(id: number) {
  return requestClient.get(`/release/release-records/${id}/`);
}

/** 触发构建 */
export function triggerBuild(releaseId: number) {
  return requestClient.post(`/release/release-records/${releaseId}/trigger/`);
}

/** 取消发布 */
export function cancelRelease(releaseId: number) {
  return requestClient.post(`/release/release-records/${releaseId}/cancel/`);
}

/** 重试构建 */
export function retryBuild(releaseId: number) {
  return requestClient.post(`/release/release-records/${releaseId}/retry/`);
}

/** 获取构建日志 */
export function getBuildLogs(releaseId: number) {
  return requestClient.get(`/release/release-records/${releaseId}/logs/`);
}

/** 审批通过 */
export function approveRelease(releaseId: number, data: { comment?: string }) {
  return requestClient.post(`/release/release-records/${releaseId}/approve/`, data);
}

/** 审批拒绝 */
export function rejectRelease(releaseId: number, data: { comment?: string }) {
  return requestClient.post(`/release/release-records/${releaseId}/reject/`, data);
}

// ============================================================
// 应用发布 API
// ============================================================

/** 触发发布（创建发布记录） */
export function triggerRelease(appId: number, data: ReleaseParams) {
  return requestClient.post(`/release/application/${appId}/release/`, data);
}

/** 获取应用分支列表 */
export function getAppBranches(appId: number) {
  return requestClient.get(`/release/application/${appId}/branches/`);
}

/** 获取应用环境配置 */
export function getAppEnvironments(appId: number) {
  return requestClient.get(`/release/application/${appId}/environments/`);
}

// ============================================================
// 用户 API
// ============================================================

/** 获取用户列表（用于审批人选择） */
export function getUserList(params?: {
  username?: string;
  search?: string;
  page?: number;
  pageSize?: number;
}) {
  return requestClient.get('/system/user/', { params });
}

// ============================================================
// 类型定义
// ============================================================

export interface ReleaseParams {
  branch: string;
  environment: string;
  version?: string;
  require_approval?: boolean;
  approval_type?: string;
  approvers?: Array<{ id: number; name: string }>;
  remark?: string;
}

export interface ReleaseRecord {
  id: number;
  application: number;
  application_name: string;
  application_code: string;
  project_name: string;
  module_name: string;
  branch: string;
  environment: string;
  environment_display: string;
  version: string;
  require_approval: boolean;
  approval_type: string;
  approvers: any[];
  approval_time: string;
  approval_user: string;
  approval_comment: string;
  jenkins_job_name: string;
  jenkins_build_number: number;
  jenkins_build_url: string;
  jenkins_build_status: string;
  jenkins_build_duration: number;
  docker_image: string;
  artifact_url: string;
  status: string;
  status_display: string;
  status_message: string;
  released_by: string;
  create_time: string;
  update_time: string;
}

export interface BuildLog {
  id: number;
  release: number;
  log_content: string;
  log_type: string;
  stage_name: string;
  stage_status: string;
  create_time: string;
}

export interface Environment {
  code: string;
  name: string;
  has_pipeline_config: boolean;
  requires_approval: boolean;
}

export interface Branch {
  name: string;
  commit?: {
    id: string;
    message: string;
    author_name: string;
  };
}

export interface UserOption {
  id: number;
  username: string;
  nickname: string;
  email: string;
}

// 发布状态映射
export const RELEASE_STATUS_MAP: Record<string, { text: string; color: string }> = {
  pending: { text: '待发布', color: 'default' },
  approval_pending: { text: '待审批', color: 'warning' },
  approved: { text: '已审批', color: 'success' },
  rejected: { text: '已拒绝', color: 'error' },
  building: { text: '构建中', color: 'processing' },
  build_success: { text: '构建成功', color: 'success' },
  build_failed: { text: '构建失败', color: 'error' },
  deploying: { text: '部署中', color: 'processing' },
  deployed: { text: '已部署', color: 'success' },
  rollback: { text: '已回滚', color: 'warning' },
  cancelled: { text: '已取消', color: 'default' },
};

// 环境选项
export const ENVIRONMENT_OPTIONS = [
  { label: '开发环境', value: 'dev' },
  { label: '测试环境', value: 'test' },
  { label: '准生产环境', value: 'staging' },
  { label: '生产环境', value: 'production' },
];
