import type { VxeTableGridOptions } from '@vben/plugins/vxe-table';

import type { VbenFormSchema } from '#/adapter/form';
import type { OnActionClickFn } from '#/adapter/vxe-table';
import type { CodeRepositoryApi } from '#/api/release/codeRepository';

import { z } from '#/adapter/form';
import { getProjectList, getModuleList } from '#/api/release';
import { REPOSITORY_TYPE_OPTIONS } from '#/api/release/codeRepository';
import { $t } from '#/locales';

/**
 * 获取表格搜索表单配置
 */
export function useGridFormSchema(): VbenFormSchema[] {
  return [
    {
      component: 'Input',
      fieldName: 'name',
      label: '仓库名称',
      componentProps: {
        placeholder: '请输入仓库名称',
        allowClear: true,
      },
    },
    {
      component: 'Input',
      fieldName: 'code',
      label: '仓库编码',
      componentProps: {
        placeholder: '请输入仓库编码',
        allowClear: true,
      },
    },
    {
      component: 'ApiSelect',
      fieldName: 'project',
      label: '所属项目',
      componentProps: {
        api: () => getProjectList({ page: 1, pageSize: 999 }),
        resultField: 'items',
        labelField: 'name',
        valueField: 'id',
        placeholder: '请选择所属项目',
        showSearch: true,
        allowClear: true,
      },
    },
    {
      component: 'ApiSelect',
      fieldName: 'module',
      label: '所属模块',
      componentProps: {
        api: getModuleList,
        resultField: 'items',
        labelField: 'name',
        valueField: 'id',
        placeholder: '请先选择项目',
        showSearch: true,
        allowClear: true,
      },
      dependencies: {
        triggerFields: ['project'],
        componentProps: (values: any) => {
          const projectId = values.project;
          if (!projectId) {
            return { params: undefined, placeholder: '请先选择项目' };
          }
          return { params: { project: projectId, pageSize: 999 }, placeholder: '请选择模块' };
        },
      },
    },
    {
      component: 'Select',
      fieldName: 'repository_type',
      label: '仓库类型',
      componentProps: {
        options: REPOSITORY_TYPE_OPTIONS,
        placeholder: '请选择仓库类型',
        allowClear: true,
      },
    },
    {
      component: 'Select',
      fieldName: 'status',
      label: '状态',
      componentProps: {
        options: [
          { label: '启用', value: 1 },
          { label: '禁用', value: 0 },
        ],
        placeholder: '请选择状态',
        allowClear: true,
      },
    },
  ];
}

export function useColumns(
  onActionClick: OnActionClickFn<CodeRepositoryApi.CodeRepository>,
): VxeTableGridOptions<CodeRepositoryApi.CodeRepository>['columns'] {
  return [
    { type: 'seq', width: 60 },
    { field: 'name', title: '仓库名称', minWidth: 120 },
    { field: 'code', title: '仓库编码', minWidth: 100 },
    { field: 'project_name', title: '所属项目', minWidth: 100 },
    { field: 'module_name', title: '所属模块', minWidth: 100 },
    { field: 'app_count', title: '应用数', width: 80, align: 'center', slots: { default: 'app_count' } },
    { field: 'gitlab_project_id', title: 'GitLab ID', width: 90 },
    { field: 'git_url', title: 'Git仓库地址', minWidth: 280, slots: { default: 'git_url' } },
    {
      field: 'repository_type',
      title: '仓库类型',
      width: 90,
      slots: { default: 'repository_type' },
    },
    {
      field: 'status',
      title: '状态',
      width: 70,
      slots: { default: 'status' },
    },
    {
      field: 'create_time',
      title: '创建时间',
      width: 160,
      formatter: ({ cellValue }) => {
        return cellValue ? new Date(cellValue).toLocaleString() : '-';
      },
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

export function useFormSchema(): VbenFormSchema[] {
  return [
    {
      component: 'Input',
      fieldName: 'name',
      label: '仓库名称',
      componentProps: {
        placeholder: '请输入仓库名称',
      },
      rules: 'required',
    },
    {
      component: 'Input',
      fieldName: 'code',
      label: '仓库编码',
      componentProps: {
        placeholder: '请输入仓库编码',
      },
      rules: 'required',
    },
    {
      component: 'ApiSelect',
      fieldName: 'project',
      label: '所属项目',
      componentProps: {
        api: () => getProjectList({ page: 1, pageSize: 999 }),
        resultField: 'items',
        labelField: 'name',
        valueField: 'id',
        placeholder: '请选择所属项目',
        showSearch: true,
      },
      rules: 'required',
    },
    {
      component: 'ApiSelect',
      fieldName: 'module',
      label: '所属模块',
      componentProps: {
        api: () => getModuleList({ page: 1, pageSize: 999 }),
        resultField: 'items',
        labelField: 'name',
        valueField: 'id',
        placeholder: '请选择所属模块（可选）',
        showSearch: true,
        allowClear: true,
      },
    },
    {
      component: 'Select',
      fieldName: 'repository_type',
      label: '仓库类型',
      componentProps: {
        options: REPOSITORY_TYPE_OPTIONS,
        placeholder: '请选择仓库类型',
      },
      defaultValue: 'gitlab',
      rules: 'required',
    },
    {
      component: 'Input',
      fieldName: 'git_url',
      label: 'Git SSH 地址',
      componentProps: {
        placeholder: '创建后自动同步到 GitLab',
        disabled: true,
      },
    },
    {
      component: 'Input',
      fieldName: 'git_http_url',
      label: 'Git HTTP 地址',
      componentProps: {
        placeholder: '创建后自动同步到 GitLab',
        disabled: true,
      },
    },
    {
      component: 'Input',
      fieldName: 'default_branch',
      label: '默认分支',
      componentProps: {
        placeholder: '默认分支，如：main',
      },
      defaultValue: 'main',
    },
    {
      component: 'Input',
      fieldName: 'description',
      label: '仓库描述',
      componentProps: {
        type: 'textarea',
        placeholder: '请输入仓库描述',
        rows: 3,
      },
    },
  ];
}
