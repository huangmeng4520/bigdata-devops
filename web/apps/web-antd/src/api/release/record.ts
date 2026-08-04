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

/** AI 分析构建失败 - 创建对话并返回 { conversation_id, content }，content 为预填到输入框的完整 prompt */
export function createAIAnalysis(releaseId: number) {
  return requestClient.post(`/release/release-records/${releaseId}/ai_analysis/`);
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
// 发布统计 API
// ============================================================

/** 获取发布统计数据 */
export function getReleaseStatistics(params?: { start_date?: string; end_date?: string }) {
  return requestClient.get('/release/statistics/', { params });
}

/** 获取发布趋势数据 */
export function getReleaseTrend(params?: { days?: number }) {
  return requestClient.get('/release/statistics/trend/', { params });
}

/** 获取应用发布排行 */
export function getAppReleaseRank(params?: { limit?: number }) {
  return requestClient.get('/release/statistics/app-rank/', { params });
}

// ============================================================
// 类型定义
// ============================================================

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
  remark?: string;
  create_time: string;
  update_time: string;
  // ===== 应用×环境级审批机制扩展字段（可选） =====
  /** 审批作用域：application/project/global */
  approval_scope?: 'application' | 'global' | 'project';
  /** 已通过审批数 */
  approved_count?: number;
  /** 需要通过审批数 */
  required_count?: number;
  /** 当前待审批人 id 列表 */
  current_approver_ids?: number[];
  /** 当前待审批人姓名列表（列表页直接展示，避免额外请求） */
  current_approver_names?: string[];
  /** 审批截止时间 */
  approval_deadline?: string;
  /** 审批规则名称 */
  approval_rule_name?: string;
  /** 审批规则编码 */
  approval_rule_code?: string;
  /** 规则类型展示文案 */
  rule_type_display?: string;
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

// 环境映射
export const ENVIRONMENT_MAP: Record<string, string> = {
  dev: '开发环境',
  test: '测试环境',
  staging: '准生产环境',
  production: '生产环境',
};
