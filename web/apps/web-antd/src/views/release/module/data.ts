import type { VxeTableGridOptions } from '@vben/plugins/vxe-table';

import type { VbenFormSchema } from '#/adapter/form';
import type { OnActionClickFn } from '#/adapter/vxe-table';
import type { ReleaseModuleApi } from '#/api/release';

import type { Ref } from 'vue';

import { z } from '#/adapter/form';
import { getProjectList } from '#/api/release';
import { $t } from '#/locales';
import { format_datetime } from '#/utils/date';
import { op } from '#/utils/permission';

export interface ModuleColumnOptions {
  onActionClick?: OnActionClickFn<ReleaseModuleApi.Module>;
  goToAppList?: (row: ReleaseModuleApi.Module) => void;
  goToRepoList?: (row: ReleaseModuleApi.Module) => void;
}

/**
 * 获取编辑表单的字段配置
 */
export function useSchema(): VbenFormSchema[] {
  return [
    {
      component: 'ApiSelect',
      fieldName: 'project',
      label: '所属项目',
      rules: z.number({ required_error: '请选择所属项目' }),
      componentProps: {
        api: () => getProjectList({ page: 1, pageSize: 999, status: 1 }),
        resultField: 'items',
        labelField: 'name',
        valueField: 'id',
        placeholder: '请选择所属项目',
        showSearch: true,
        filterOption: (input: string, option: { label: string }) =>
          option.label.toLowerCase().includes(input.toLowerCase()),
      },
    },
    {
      component: 'Input',
      fieldName: 'name',
      label: '模块名称',
      rules: z
        .string()
        .min(2, '模块名称至少2个字符')
        .max(50, '模块名称最多50个字符'),
    },
    {
      component: 'Input',
      fieldName: 'code',
      label: '模块编码',
      rules: z
        .string()
        .min(2, '模块编码至少2个字符')
        .max(30, '模块编码最多30个字符')
        .regex(/^[a-zA-Z][a-zA-Z0-9_-]*$/, '编码必须以字母开头，只能包含字母、数字、下划线和横杠'),
    },
    {
      component: 'Textarea',
      fieldName: 'description',
      label: '模块描述',
      componentProps: {
        maxLength: 200,
        rows: 3,
        showCount: true,
      },
    },
    {
      component: 'InputNumber',
      fieldName: 'gitlab_subgroup_id',
      label: 'GitLab Subgroup ID',
      componentProps: {
        placeholder: '可选，关联的GitLab Subgroup ID',
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
export function useGridFormSchema(
  projectOptions?: Ref<{ label: string; value: number }[]>,
): VbenFormSchema[] {
  return [
    {
      component: 'Select',
      fieldName: 'project',
      label: '所属项目',
      componentProps: {
        allowClear: true,
        placeholder: '请选择项目',
        options: projectOptions,
        showSearch: true,
        filterOption: (input: string, option: { label: string }) =>
          option.label.toLowerCase().includes(input.toLowerCase()),
      },
    },
    {
      component: 'Input',
      fieldName: 'name',
      label: '模块名称',
      componentProps: { allowClear: true, placeholder: '请输入模块名称' },
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
  options?: ModuleColumnOptions,
): VxeTableGridOptions<ReleaseModuleApi.Module>['columns'] {
  const { onActionClick, goToAppList, goToRepoList } = options || {};
  return [
    {
      type: 'seq',
      title: '序号',
      width: 60,
    },
    {
      field: 'project_name',
      title: '所属项目',
      width: 150,
    },
    {
      field: 'name',
      title: '模块名称',
      minWidth: 150,
    },
    {
      field: 'code',
      title: '模块编码',
      width: 150,
    },
    {
      field: 'repo_count',
      title: '仓库数',
      width: 80,
      align: 'center',
      slots: { default: 'repo_count' },
    },
    {
      field: 'app_count',
      title: '应用数',
      width: 80,
      align: 'center',
      slots: { default: 'app_count' },
    },
    {
      title: 'GitLab',
      width: 140,
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
      slots: { default: 'operation' },
      field: 'operation',
      fixed: 'right',
      headerAlign: 'center',
      showOverflow: false,
      title: '操作',
      width: 200,
    },
  ];
}
