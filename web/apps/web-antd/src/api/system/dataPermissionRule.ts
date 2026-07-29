import { requestClient } from '#/api/request';

/**
 * 数据权限规则（应用权限分配）接口
 *
 * 后端对应 system:data_permission_rule 视图集。
 * 资源范围约定：scope_type='application'，scope_id=应用主键。
 */
export namespace DataPermissionRuleApi {
  /** 某资源范围下已分配的用户 */
  export interface ScopeUser {
    user_id: number;
    username: string;
    nickname: string;
    level: string;
  }

  /** 反向：某用户被授予的资源范围 */
  export interface UserScope {
    scope_type: string;
    scope_id: number;
    level: string;
    username: string;
    nickname: string;
  }

  /** 批量分配入参（覆盖式） */
  export interface AssignParams {
    scope_type: string;
    scope_id: number;
    user_ids: number[];
    level?: string;
  }

  /** 规则列表项 */
  export interface RuleListItem {
    id: number;
    scope_type: string;
    scope_id: number;
    user_id: number;
    level: string;
    username?: string;
    nickname?: string;
  }
}

/** 获取某资源范围下已分配的用户 */
export function getScopeUsers(params: {
  scope_type: string;
  scope_id: number;
}) {
  return requestClient.get<DataPermissionRuleApi.ScopeUser[]>(
    '/system/data_permission_rule/scope_users/',
    { params },
  );
}

/** 反向查询：某用户被授予的资源范围 */
export function getUserScopes(params: {
  user_id?: number;
  scope_type?: string;
}) {
  return requestClient.get<DataPermissionRuleApi.UserScope[]>(
    '/system/data_permission_rule/user_scopes/',
    { params },
  );
}

/** 批量分配（覆盖式：替换该范围下原有分配） */
export function assignDataPermission(data: DataPermissionRuleApi.AssignParams) {
  return requestClient.post<{ count: number }>(
    '/system/data_permission_rule/assign/',
    data,
  );
}

/** 规则列表 */
export function getDataPermissionRules(params?: Record<string, any>) {
  return requestClient.get<{ total: number; items: DataPermissionRuleApi.RuleListItem[] }>(
    '/system/data_permission_rule/',
    { params },
  );
}

/** 规则详情 */
export function getDataPermissionRule(id: number) {
  return requestClient.get<DataPermissionRuleApi.RuleListItem>(
    `/system/data_permission_rule/${id}/`,
  );
}

/** 创建规则 */
export function createDataPermissionRule(
  data: Partial<DataPermissionRuleApi.RuleListItem>,
) {
  return requestClient.post<DataPermissionRuleApi.RuleListItem>(
    '/system/data_permission_rule/',
    data,
  );
}

/** 更新规则 */
export function updateDataPermissionRule(
  id: number,
  data: Partial<DataPermissionRuleApi.RuleListItem>,
) {
  return requestClient.put<DataPermissionRuleApi.RuleListItem>(
    `/system/data_permission_rule/${id}/`,
    data,
  );
}

/** 删除规则 */
export function deleteDataPermissionRule(id: number) {
  return requestClient.delete(`/system/data_permission_rule/${id}/`);
}
