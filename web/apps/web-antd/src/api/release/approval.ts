import { requestClient } from '#/api/request';

/**
 * 审批进度与审批待办 API
 */

export namespace ApprovalApi {
  /** 审批历史记录条目 */
  export interface ApprovalRecordItem {
    approver_id: number;
    approver_name: string;
    /** 顺序号（顺序审批时使用） */
    order?: number;
    /** 操作类型：approve/reject/transfer/add_sign */
    action: 'add_sign' | 'approve' | 'reject' | 'transfer';
    action_display?: string;
    /** 审批意见 */
    comment?: string;
    /** 操作时间 */
    acted_at?: string;
  }

  /** 审批进度视图
   * 由 release-records/{id}/approval_progress/ 返回
   */
  export interface ApprovalProgress {
    /** 规则类型 */
    rule_type?: 'all' | 'any' | 'sequential' | 'single';
    /** 作用域 */
    scope?: 'application' | 'global' | 'project';
    /** 规则名称 */
    rule_name?: string;
    /** 规则编码 */
    rule_code?: string;
    rule_type_display?: string;
    /** 已通过数 */
    approved_count: number;
    /** 需要通过数 */
    required_count: number;
    /** 当前待审批人 id 列表 */
    current_approver_ids: number[];
    /** 当前待审批人姓名列表 */
    current_approver_names?: string[];
    /** 审批截止时间 */
    deadline?: string;
    /** 全部审批人列表 */
    approvers?: Array<{
      user_id: number;
      username: string;
      order?: number;
    }>;
    /** 审批历史时间线 */
    history?: ApprovalRecordItem[];
  }

  /** 我的审批待办查询参数 */
  export interface MyApprovalTasksParams {
    page?: number;
    pageSize?: number;
    status?: string;
    environment?: string;
  }
}

/**
 * 获取发布记录的审批进度
 */
async function getApprovalProgress(releaseId: number) {
  return requestClient.get<ApprovalApi.ApprovalProgress>(
    `/release/release-records/${releaseId}/approval_progress/`,
  );
}

/**
 * 获取我的审批待办（分页）
 */
async function getMyApprovalTasks(params?: ApprovalApi.MyApprovalTasksParams) {
  return requestClient.get<{
    items: any[];
    total: number;
  }>('/release/release-records/my_approval_tasks/', {
    params,
  });
}

export { getApprovalProgress, getMyApprovalTasks };
