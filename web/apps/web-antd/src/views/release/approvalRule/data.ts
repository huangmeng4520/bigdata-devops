import type { ApprovalRuleApi } from '#/api/release';

import { h } from 'vue';

import { Tag } from 'ant-design-vue';

import type { VbenFormSchema } from '#/adapter/form';

import { SCOPE_LABEL_MAP } from '#/api/release';

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
      title: '规则名称',
      minWidth: 160,
    },
    {
      field: 'code',
      title: '规则编码',
      width: 160,
    },
    {
      field: 'scope',
      title: '作用域',
      width: 90,
      slots: {
        default: ({ row }: { row: ApprovalRuleApi.ApprovalRule }) => {
          const text = SCOPE_LABEL_MAP[row.scope] || row.scope || '-';
          const colorMap: Record<string, string> = {
            application: 'blue',
            project: 'cyan',
            global: 'purple',
          };
          return h(Tag, { color: colorMap[row.scope] || 'default' }, () => text);
        },
      },
    },
    {
      field: 'project_name',
      title: '项目',
      width: 120,
      slots: {
        default: ({ row }: { row: ApprovalRuleApi.ApprovalRule }) =>
          row.project_name || '-',
      },
    },
    {
      field: 'application_name',
      title: '应用',
      width: 140,
      slots: {
        default: ({ row }: { row: ApprovalRuleApi.ApprovalRule }) =>
          row.application_name || '-',
      },
    },
    {
      field: 'environment',
      title: '环境',
      width: 100,
      slots: {
        default: ({ row }: { row: ApprovalRuleApi.ApprovalRule }) => {
          const envMap: Record<string, { color: string; text: string }> = {
            dev: { color: 'default', text: '开发' },
            test: { color: 'blue', text: '测试' },
            staging: { color: 'orange', text: '准生产' },
            production: { color: 'red', text: '生产' },
          };
          const item = envMap[row.environment] || {
            color: 'default',
            text: row.environment,
          };
          return h(Tag, { color: item.color }, () => item.text);
        },
      },
    },
    {
      field: 'rule_type_display',
      title: '规则类型',
      width: 120,
      slots: {
        default: ({ row }: { row: ApprovalRuleApi.ApprovalRule }) =>
          row.rule_type_display || row.rule_type || '-',
      },
    },
    {
      field: 'approvers',
      title: '审批人',
      minWidth: 160,
      slots: {
        // 审批人数组渲染为逗号分隔的用户名
        default: ({ row }: { row: ApprovalRuleApi.ApprovalRule }) => {
          if (!row.approvers || row.approvers.length === 0) return '-';
          return row.approvers
            .map((a) => {
              const order = a.order ? `[${a.order}]` : '';
              return `${a.username}${order}`;
            })
            .join('、');
        },
      },
    },
    {
      field: 'timeout_hours',
      title: '超时(小时)',
      width: 100,
      slots: {
        default: ({ row }: { row: ApprovalRuleApi.ApprovalRule }) =>
          row.timeout_hours ? `${row.timeout_hours}h` : '-',
      },
    },
    {
      field: 'timeout_action_display',
      title: '超时策略',
      width: 100,
      slots: {
        default: ({ row }: { row: ApprovalRuleApi.ApprovalRule }) =>
          row.timeout_action_display || '-',
      },
    },
    {
      field: 'status',
      title: '状态',
      width: 80,
      slots: {
        default: ({ row }: { row: ApprovalRuleApi.ApprovalRule }) => {
          return h(
            Tag,
            { color: row.status === 1 ? 'success' : 'error' },
            () => (row.status === 1 ? '启用' : '禁用'),
          );
        },
      },
    },
    {
      field: 'action',
      title: '操作',
      width: 160,
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
      component: 'Input',
      componentProps: {
        placeholder: '请输入规则名称',
      },
      fieldName: 'name',
      label: '名称',
    },
    {
      component: 'Select',
      componentProps: {
        options: [
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
        options: [
          { label: '应用级', value: 'application' },
          { label: '项目级', value: 'project' },
          { label: '全局', value: 'global' },
        ],
        placeholder: '请选择作用域',
        allowClear: true,
      },
      fieldName: 'scope',
      label: '作用域',
    },
    {
      component: 'Select',
      componentProps: {
        options: [
          { label: '启用', value: 1 },
          { label: '禁用', value: 0 },
        ],
        placeholder: '请选择状态',
        allowClear: true,
      },
      fieldName: 'status',
      label: '状态',
    },
  ];
}
