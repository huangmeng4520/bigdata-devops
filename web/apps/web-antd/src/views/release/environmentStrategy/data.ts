import type { EnvironmentStrategyApi } from '#/api/release';

import { h } from 'vue';

import { Tag } from 'ant-design-vue';

import { PIPELINE_MODE_OPTIONS } from '#/api/release';

import type { VbenFormSchema } from '#/adapter/form';

/**
 * 表格列配置
 */
export function useColumns() {
  return [
    {
      type: 'seq',
      title: '序号',
      width: 60,
    },
    {
      field: 'name',
      title: '策略名称',
      minWidth: 180,
    },
    {
      field: 'code',
      title: '策略编码',
      width: 160,
    },
    {
      field: 'environment',
      title: '环境',
      width: 100,
      slots: {
        default: ({ row }: { row: EnvironmentStrategyApi.Strategy }) => {
          const envMap: Record<string, { color: string; text: string }> = {
            dev: { color: 'default', text: '开发' },
            test: { color: 'blue', text: '测试' },
            staging: { color: 'orange', text: '准生产' },
            production: { color: 'red', text: '生产' },
          };
          const item = envMap[row.environment] || { color: 'default', text: row.environment };
          return h(Tag, { color: item.color }, () => item.text);
        },
      },
    },
    {
      field: 'pipeline_mode',
      title: '流水线模式',
      width: 120,
      slots: {
        default: ({ row }: { row: EnvironmentStrategyApi.Strategy }) => {
          const modeMap: Record<string, { color: string; text: string }> = {
            integrated: { color: 'green', text: 'CI/CD合并' },
            separated: { color: 'purple', text: 'CI/CD分离' },
          };
          const item = modeMap[row.pipeline_mode] || { color: 'default', text: row.pipeline_mode };
          return h(Tag, { color: item.color }, () => item.text);
        },
      },
    },
    {
      field: 'requires_approval',
      title: '审批',
      width: 80,
      slots: {
        default: ({ row }: { row: EnvironmentStrategyApi.Strategy }) => {
          return h(Tag, { color: row.requires_approval ? 'warning' : 'default' }, () => row.requires_approval ? '需要' : '不需要');
        },
      },
    },
    {
      field: 'auto_deploy',
      title: '自动部署',
      width: 90,
      slots: {
        default: ({ row }: { row: EnvironmentStrategyApi.Strategy }) => {
          return h(Tag, { color: row.auto_deploy ? 'success' : 'default' }, () => row.auto_deploy ? '是' : '否');
        },
      },
    },
    {
      field: 'is_default',
      title: '默认策略',
      width: 90,
      slots: {
        default: ({ row }: { row: EnvironmentStrategyApi.Strategy }) => {
          return h(Tag, { color: row.is_default ? 'gold' : 'default' }, () => row.is_default ? '默认' : '-');
        },
      },
    },
    {
      field: 'status',
      title: '状态',
      width: 80,
      slots: {
        default: ({ row }: { row: EnvironmentStrategyApi.Strategy }) => {
          return h(Tag, { color: row.status === 1 ? 'success' : 'error' }, () => row.status === 1 ? '启用' : '禁用');
        },
      },
    },
    {
      field: 'action',
      title: '操作',
      width: 180,
      fixed: 'right',
      slots: { default: 'action' },
    },
  ];
}

/**
 * 搜索表单配置
 */
export function useGridFormSchema(): VbenFormSchema[] {
  return [
    {
      component: 'Select',
      componentProps: {
        options: [
          { label: '全部', value: '' },
          { label: '开发环境', value: 'dev' },
          { label: '测试环境', value: 'test' },
          { label: '准生产环境', value: 'staging' },
          { label: '生产环境', value: 'production' },
        ],
        placeholder: '请选择环境',
        allowClear: true,
      },
      fieldName: 'environment',
      label: '环境',
    },
    {
      component: 'Select',
      componentProps: {
        options: [{ label: '全部', value: '' }, ...PIPELINE_MODE_OPTIONS],
        placeholder: '请选择模式',
        allowClear: true,
      },
      fieldName: 'pipeline_mode',
      label: '模式',
    },
    {
      component: 'Input',
      componentProps: {
        placeholder: '请输入策略名称',
      },
      fieldName: 'name',
      label: '名称',
    },
  ];
}

/**
 * 环境选项
 */
export function getEnvironmentOptions() {
  return [
    { label: '开发环境', value: 'dev' },
    { label: '测试环境', value: 'test' },
    { label: '准生产环境', value: 'staging' },
    { label: '生产环境', value: 'production' },
  ];
}

/**
 * 流水线模式选项
 */
export function getPipelineModeOptions() {
  return PIPELINE_MODE_OPTIONS;
}
