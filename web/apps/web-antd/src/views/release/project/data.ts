import type { VxeTableGridOptions } from '@vben/plugins/vxe-table';

import type { VbenFormSchema } from '#/adapter/form';
import type { OnActionClickFn } from '#/adapter/vxe-table';
import type { ReleaseProjectApi } from '#/api/release';

import { z } from '#/adapter/form';
import { $t } from '#/locales';
import { format_datetime } from '#/utils/date';
import { op } from '#/utils/permission';

/**
 * 获取编辑表单的字段配置
 */
export function useSchema(): VbenFormSchema[] {
  return [
    {
      component: 'Input',
      fieldName: 'name',
      label: '项目名称',
      rules: z
        .string()
        .min(2, '项目名称至少2个字符')
        .max(50, '项目名称最多50个字符'),
    },
    {
      component: 'Input',
      fieldName: 'code',
      label: '项目编码',
      rules: z
        .string()
        .min(2, '项目编码至少2个字符')
        .max(30, '项目编码最多30个字符')
        .regex(/^[a-zA-Z][a-zA-Z0-9_-]*$/, '编码必须以字母开头，只能包含字母、数字、下划线和横杠'),
    },
    {
      component: 'Textarea',
      fieldName: 'description',
      label: '项目描述',
      componentProps: {
        maxLength: 200,
        rows: 3,
        showCount: true,
      },
    },
    {
      component: 'InputNumber',
      fieldName: 'gitlab_group_id',
      label: 'GitLab Group ID',
      componentProps: {
        placeholder: '可选，关联的GitLab Group ID',
        min: 1,
      },
    },
    {
      component: 'InputNumber',
      fieldName: 'sort',
      label: '显示排序',
      componentProps: {
        min: 0,
        max: 999,
      },
      defaultValue: 0,
    },
    {
      component: 'RadioGroup',
      componentProps: {
        buttonStyle: 'solid',
        options: [
          { label: $t('common.enabled'), value: 1 },
          { label: $t('common.disabled'), value: 0 },
        ],
        optionType: 'button',
      },
      defaultValue: 1,
      fieldName: 'status',
      label: '状态',
    },
    {
      component: 'Textarea',
      componentProps: {
        maxLength: 100,
        rows: 2,
        showCount: true,
      },
      fieldName: 'remark',
      label: '备注',
    },
  ];
}

/**
 * 获取表格搜索表单配置
 */
export function useGridFormSchema(): VbenFormSchema[] {
  return [
    {
      component: 'Input',
      fieldName: 'name',
      label: '项目名称',
      componentProps: { allowClear: true, placeholder: '请输入项目名称' },
    },
    {
      component: 'Input',
      fieldName: 'code',
      label: '项目编码',
      componentProps: { allowClear: true, placeholder: '请输入项目编码' },
    },
    {
      component: 'Select',
      fieldName: 'status',
      label: '状态',
      componentProps: {
        allowClear: true,
        options: [
          { label: $t('common.enabled'), value: 1 },
          { label: $t('common.disabled'), value: 0 },
        ],
      },
    },
  ];
}

/**
 * 获取表格列配置
 * @param onActionClick 表格操作按钮点击事件
 */
export function useColumns(
  onActionClick?: OnActionClickFn<ReleaseProjectApi.Project>,
): VxeTableGridOptions<ReleaseProjectApi.Project>['columns'] {
  return [
    {
      type: 'seq',
      title: '序号',
      width: 60,
    },
    {
      field: 'name',
      title: '项目名称',
      minWidth: 150,
    },
    {
      field: 'code',
      title: '项目编码',
      width: 150,
    },
    {
      title: '模块数',
      width: 80,
      align: 'center',
      slots: { default: 'module_count' },
    },
    {
      title: '应用数',
      width: 80,
      align: 'center',
      slots: { default: 'app_count' },
    },
    {
      title: 'GitLab',
      width: 100,
      align: 'center',
      slots: { default: 'gitlab_status' },
    },
    {
      cellRender: { name: 'CellTag' },
      field: 'status',
      title: '状态',
      width: 100,
    },
    {
      field: 'sort',
      title: '排序',
      width: 80,
      align: 'center',
    },
    {
      field: 'creator',
      title: '创建人',
      width: 100,
    },
    {
      field: 'create_time',
      title: '创建时间',
      width: 160,
      formatter: ({ cellValue }) => format_datetime(cellValue),
    },
    {
      field: 'remark',
      title: '备注',
      minWidth: 150,
      showOverflow: true,
    },
    {
      align: 'center',
      cellRender: {
        attrs: {
          nameField: 'name',
          nameTitle: '项目',
          onClick: onActionClick,
        },
        name: 'CellOperation',
        options: [
          op('release:project:edit', 'edit'),
          op('release:module:create', { code: 'create-module', text: '创建模块' }),
          op('release:project:sync-gitlab', { code: 'sync-gitlab', text: '同步GitLab' }),
          op('release:project:delete', 'delete'),
        ],
      },
      field: 'operation',
      fixed: 'right',
      headerAlign: 'center',
      showOverflow: false,
      title: '操作',
      width: 260,
    },
  ];
}
