import { requestClient } from '#/api/request';

export namespace EnvironmentStrategyApi {
  export interface Strategy {
    id: number;
    name: string;
    code: string;
    environment: string;
    requires_approval: boolean;
    auto_deploy: boolean;
    description?: string;
    is_default: boolean;
    status: number;
    status_display?: string;
    creator?: string;
    modifier?: string;
    create_time?: string;
    update_time?: string;
  }

  export interface StrategyListParams {
    page?: number;
    page_size?: number;
    name?: string;
    code?: string;
    environment?: string;
    is_default?: boolean;
    status?: number;
  }
}

/**
 * 获取策略列表
 */
async function getStrategyList(params?: EnvironmentStrategyApi.StrategyListParams) {
  return requestClient.get<{ items: EnvironmentStrategyApi.Strategy[]; total: number }>('/release/environment-strategies/', {
    params,
  });
}

/**
 * 获取策略详情
 */
async function getStrategyDetail(id: number) {
  return requestClient.get<EnvironmentStrategyApi.Strategy>(`/release/environment-strategies/${id}/`);
}

/**
 * 创建策略
 */
async function createStrategy(data: Partial<EnvironmentStrategyApi.Strategy>) {
  return requestClient.post<EnvironmentStrategyApi.Strategy>('/release/environment-strategies/', data);
}

/**
 * 更新策略
 */
async function updateStrategy(id: number, data: Partial<EnvironmentStrategyApi.Strategy>) {
  return requestClient.put<EnvironmentStrategyApi.Strategy>(`/release/environment-strategies/${id}/`, data);
}

/**
 * 删除策略
 */
async function deleteStrategy(id: number) {
  return requestClient.delete(`/release/environment-strategies/${id}/`);
}

/**
 * 按环境获取策略
 */
async function getStrategiesByEnvironment(environment: string) {
  return requestClient.get<{ data: EnvironmentStrategyApi.Strategy[] }>('/release/environment-strategies/by_environment/', {
    params: { environment },
  });
}

/**
 * 获取默认策略
 */
async function getDefaultStrategies() {
  return requestClient.get<{ data: EnvironmentStrategyApi.Strategy[] }>('/release/environment-strategies/defaults/');
}

/**
 * 设置为默认策略
 */
async function setDefaultStrategy(id: number) {
  return requestClient.post(`/release/environment-strategies/${id}/set_default/`);
}

export {
  createStrategy,
  getDefaultStrategies,
  getStrategiesByEnvironment,
  getStrategyDetail,
  getStrategyList,
  setDefaultStrategy,
  deleteStrategy,
  updateStrategy,
};
