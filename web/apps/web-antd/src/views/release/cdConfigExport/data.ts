import type { CDConfigExportApi } from '#/api/release';

import { h } from 'vue';

import { Tag } from 'ant-design-vue';

import { EXPORT_FORMAT_OPTIONS } from '#/api/release';

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
      field: 'application_name',
      title: '应用名称',
      minWidth: 150,
    },
    {
      field: 'environment',
      title: '环境',
      width: 100,
      slots: {
        default: ({ row }: { row: CDConfigExportApi.Export }) => {
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
      field: 'config_version',
      title: '配置版本',
      width: 100,
      slots: {
        default: ({ row }: { row: CDConfigExportApi.Export }) => {
          return `v${row.config_version}`;
        },
      },
    },
    {
      field: 'export_format',
      title: '导出格式',
      width: 100,
      slots: {
        default: ({ row }: { row: CDConfigExportApi.Export }) => {
          const formatMap: Record<string, { color: string; text: string }> = {
            jenkinsfile: { color: 'blue', text: 'Jenkinsfile' },
            json: { color: 'green', text: 'JSON' },
            yaml: { color: 'orange', text: 'YAML' },
            zip: { color: 'purple', text: 'ZIP' },
          };
          const item = formatMap[row.export_format] || { color: 'default', text: row.export_format };
          return h(Tag, { color: item.color }, () => item.text);
        },
      },
    },
    {
      field: 'exported_by',
      title: '导出人',
      width: 100,
    },
    {
      field: 'download_count',
      title: '下载次数',
      width: 100,
    },
    {
      field: 'create_time',
      title: '导出时间',
      width: 160,
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
        options: [{ label: '全部', value: '' }, ...EXPORT_FORMAT_OPTIONS],
        placeholder: '请选择格式',
        allowClear: true,
      },
      fieldName: 'export_format',
      label: '格式',
    },
  ];
}

/**
 * 导出格式选项
 */
export function getExportFormatOptions() {
  return EXPORT_FORMAT_OPTIONS;
}
