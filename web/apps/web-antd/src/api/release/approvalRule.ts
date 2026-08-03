import { requestClient } from '#/api/request';

/**
 * 审批规则作用域：应用级 / 项目级 / 全局
 */

export namespace ApprovalRuleApi {
  /** 审批人 */
  export interface Approver {
    user_id: number;
    username: string;
    order?: number;
  }

  /** 审批规则
   * 后端 ApprovalRule 模型序列化后的结构
   */
  export interface ApprovalRule {
    id: number;
    name: string;
    code: string;
    /** 项目 id（应用级/项目级规则可为 null） */
    project: number | null;
    project_name?: string;
    /** 应用 id（仅应用级规则非 null） */
    application: number | null;
    application_name?: string;
    /** 环境：dev/test/staging/production */
    environment: string;
    /** 规则类型：single/any/all/sequential */
    rule_type: 'all' | 'any' | 'sequential' | 'single';
    rule_type_display?: string;
    /** 审批人列表 */
    approvers: Approver[];
    /** 最少通过人数（rule_type=any 时生效） */
    min_approvers: number;
    /** 超时小时数 */
    timeout_hours: number;
    /** 超时策略：reject/notify/auto_approve */
    timeout_action: 'auto_approve' | 'notify' | 'reject';
    timeout_action_display?: string;
    /** 通知渠道：site/email/feishu */
    notify_channels: string[];
    /** 是否默认规则 */
    is_default: boolean;
    /** 作用域：application/project/global（后端计算属性） */
    scope: 'application' | 'global' | 'project';
    /** 状态：1 启用 / 0 禁用 */
    status: number;
    status_display?: string;
    creator?: string;
    modifier?: string;
    create_time?: string;
    update_time?: string;
  }

  /** 列表查询参数（支持 project、application、scope、environment 过滤） */
  export interface ApprovalRuleListParams {
    page?: number;
    page_size?: number;
    name?: string;
    code?: string;
    project?: number;
    application?: number;
    scope?: 'application' | 'global' | 'project';
    environment?: string;
    status?: number;
  }

  /** 按作用域查询参数 */
  export interface ByScopeParams {
    project_id?: number;
    application_id?: number;
    environment?: string;
  }

  /** 生效规则查询参数 */
  export interface EffectiveRuleParams {
    application_id: number;
    environment: string;
  }
}

// ============================================================
// 常量定义
// ============================================================

/** 规则类型选项 */
export const RULE_TYPE_OPTIONS = [
  { label: '单人审批', value: 'single' },
  { label: '会签（任一通过）', value: 'any' },
  { label: '会签（全部通过）', value: 'all' },
  { label: '顺序审批', value: 'sequential' },
];

/** 超时策略选项 */
export const TIMEOUT_ACTION_OPTIONS = [
  { label: '自动拒绝', value: 'reject' },
  { label: '通知提醒', value: 'notify' },
  { label: '自动通过', value: 'auto_approve' },
];

/** 通知渠道选项 */
export const NOTIFY_CHANNEL_OPTIONS = [
  { label: '站内信', value: 'site' },
  { label: '邮件', value: 'email' },
  { label: '飞书', value: 'feishu' },
];

/** 作用域中文映射 */
export const SCOPE_LABEL_MAP: Record<string, string> = {
  application: '应用级',
  project: '项目级',
  global: '全局',
};

// ============================================================
// API 函数
// ============================================================

/**
 * 获取审批规则列表
 */
async function getApprovalRules(params?: ApprovalRuleApi.ApprovalRuleListParams) {
  return requestClient.get<{
    items: ApprovalRuleApi.ApprovalRule[];
    total: number;
  }>('/release/approval-rules/', {
    params,
  });
}

/**
 * 获取审批规则详情
 */
async function getApprovalRuleDetail(id: number) {
  return requestClient.get<ApprovalRuleApi.ApprovalRule>(
    `/release/approval-rules/${id}/`,
  );
}

/**
 * 创建审批规则
 */
async function createApprovalRule(data: Partial<ApprovalRuleApi.ApprovalRule>) {
  return requestClient.post<ApprovalRuleApi.ApprovalRule>(
    '/release/approval-rules/',
    data,
  );
}

/**
 * 更新审批规则
 */
async function updateApprovalRule(
  id: number,
  data: Partial<ApprovalRuleApi.ApprovalRule>,
) {
  return requestClient.put<ApprovalRuleApi.ApprovalRule>(
    `/release/approval-rules/${id}/`,
    data,
  );
}

/**
 * 删除审批规则
 */
async function deleteApprovalRule(id: number) {
  return requestClient.delete(`/release/approval-rules/${id}/`);
}

/**
 * 按作用域查询审批规则
 * 返回应用级 + 项目级 + 全局三级合并视图
 */
async function getApprovalRulesByScope(params: ApprovalRuleApi.ByScopeParams) {
  return requestClient.get<ApprovalRuleApi.ApprovalRule[]>(
    '/release/approval-rules/by_scope/',
    { params },
  );
}

/**
 * 查询某应用某环境的生效规则
 */
async function getEffectiveRule(params: ApprovalRuleApi.EffectiveRuleParams) {
  return requestClient.get<ApprovalRuleApi.ApprovalRule | null>(
    '/release/approval-rules/effective/',
    { params },
  );
}

export {
  createApprovalRule,
  deleteApprovalRule,
  getApprovalRuleDetail,
  getApprovalRules,
  getApprovalRulesByScope,
  getEffectiveRule,
  updateApprovalRule,
};
