import type { PipelineTemplateApi } from '#/api/release';
import type { OnActionClickFn } from '#/adapter/vxe-table';

import { h } from 'vue';

import { Tag } from 'ant-design-vue';

import { LANGUAGE_OPTIONS } from '#/api/release';

import { z } from '#/adapter/form';
import type { VbenFormSchema } from '#/adapter/form';
import { op } from '#/utils/permission';

let onActionClickFn: OnActionClickFn | null = null;

export function setOnActionClick(fn: OnActionClickFn) {
  onActionClickFn = fn;
}

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
      title: '模板名称',
      minWidth: 200,
    },
    {
      field: 'code',
      title: '模板编码',
      width: 180,
    },
    {
      field: 'language',
      title: '编程语言',
      width: 100,
    },
    {
      field: 'framework',
      title: '框架',
      width: 120,
    },
    {
      field: 'is_official',
      title: '官方模板',
      width: 100,
      slots: {
        default: ({ row }: { row: PipelineTemplateApi.Template }) => {
          return h(Tag, { color: row.is_official ? 'gold' : 'default' }, () => row.is_official ? '官方' : '自定义');
        },
      },
    },
    {
      field: 'latest_version',
      title: '最新版本',
      width: 100,
      slots: {
        default: ({ row }: { row: PipelineTemplateApi.Template }) => {
          return row.latest_version?.version || '-';
        },
      },
    },
    {
      field: 'status',
      title: '状态',
      width: 80,
      slots: {
        default: ({ row }: { row: PipelineTemplateApi.Template }) => {
          return h(Tag, { color: row.status === 1 ? 'success' : 'error' }, () => row.status === 1 ? '启用' : '禁用');
        },
      },
    },
    {
      field: 'create_time',
      title: '创建时间',
      width: 160,
    },
    {
      align: 'center',
      cellRender: {
        attrs: {
          nameField: 'name',
          nameTitle: '模板',
          onClick: onActionClickFn,
        },
        name: 'CellOperation',
        options: [
          op('release:pipeline_template:edit', { code: 'edit', text: '编辑' }),
          op('release:pipeline_template:query', { code: 'versions', text: '版本管理' }),
          op('release:pipeline_template:create', { code: 'copy', text: '复制' }),
          op('release:pipeline_template:query', { code: 'export', text: '导出' }),
          op('release:pipeline_template:delete', { code: 'delete', text: '删除' }),
        ],
      },
      field: 'operation',
      fixed: 'right',
      headerAlign: 'center',
      showOverflow: false,
      title: '操作',
      width: 240,
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
        options: [{ label: '全部', value: '' }, ...LANGUAGE_OPTIONS],
        placeholder: '请选择语言',
        allowClear: true,
      },
      fieldName: 'language',
      label: '语言',
    },
    {
      component: 'Input',
      componentProps: {
        placeholder: '请输入模板名称',
      },
      fieldName: 'name',
      label: '名称',
    },
  ];
}

/**
 * 语言选项
 */
export function getLanguageOptions() {
  return LANGUAGE_OPTIONS;
}

/**
 * 获取编辑表单的字段配置
 */
export function useSchema(isEdit: boolean = false): VbenFormSchema[] {
  const baseSchema: VbenFormSchema[] = [
    {
      component: 'Input',
      fieldName: 'name',
      label: '模板名称',
      rules: z.string().min(1, '请输入模板名称'),
    },
    {
      component: 'Input',
      fieldName: 'code',
      label: '模板编码',
      rules: z.string().min(1, '请输入模板编码'),
      componentProps: { placeholder: '如: ci-java-springboot-maven' },
    },
    {
      component: 'Select',
      fieldName: 'language',
      label: '编程语言',
      rules: z.string({ required_error: '请选择编程语言' }),
      componentProps: {
        options: LANGUAGE_OPTIONS,
        style: { width: '100%' },
      },
    },
    {
      component: 'Input',
      fieldName: 'language_version',
      label: '语言版本',
      componentProps: { placeholder: '如: 17, 3.11, 18' },
    },
    {
      component: 'Input',
      fieldName: 'framework',
      label: '框架',
      componentProps: { placeholder: '如: Spring Boot, Vue, Django' },
    },
    {
      component: 'Textarea',
      fieldName: 'description',
      label: '描述',
      componentProps: { rows: 3 },
    },
    {
      component: 'Switch',
      fieldName: 'is_official',
      label: '官方模板',
    },
    {
      component: 'RadioGroup',
      fieldName: 'status',
      label: '状态',
      componentProps: {
        options: [
          { label: '启用', value: 1 },
          { label: '禁用', value: 0 },
        ],
      },
      defaultValue: 1,
    },
  ];

  return baseSchema;
}
