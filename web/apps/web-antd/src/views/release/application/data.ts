import type { VxeTableGridOptions } from '@vben/plugins/vxe-table';

import type { VbenFormSchema } from '#/adapter/form';
import type { OnActionClickFn } from '#/adapter/vxe-table';
import type { ReleaseApplicationApi } from '#/api/release';

import type { Ref } from 'vue';

import { z } from '#/adapter/form';
import { getModuleList, getProjectList } from '#/api/release';
import { getCodeRepositoryList } from '#/api/release/codeRepository';
import { APP_TYPE_OPTIONS } from '#/api/release';
import { $t } from '#/locales';
import { format_datetime } from '#/utils/date';

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
      component: 'ApiSelect',
      fieldName: 'module',
      label: '所属模块',
      componentProps: {
        api: getModuleList,
        resultField: 'items',
        labelField: 'name',
        valueField: 'id',
        placeholder: '请先选择项目（可选）',
        showSearch: true,
        immediate: false,
        allowClear: true,
        filterOption: (input: string, option: { label: string }) =>
          option.label.toLowerCase().includes(input.toLowerCase()),
      },
      dependencies: {
        triggerFields: ['project'],
        componentProps: (values) => {
          const projectId = values.project;
          if (!projectId) {
            return {
              params: undefined,
              placeholder: '请先选择项目',
            };
          }
          return {
            params: { project: projectId, status: 1, pageSize: 999 },
            placeholder: '请选择模块',
          };
        },
      },
    },
    {
      component: 'ApiSelect',
      fieldName: 'code_repository',
      label: '代码仓库',
      rules: z.number({ required_error: '请选择代码仓库' }),
      dependencies: {
        triggerFields: ['project', 'module'],
        componentProps: (values) => {
          const projectId = values.project;
          const moduleId = values.module;
          let params: any = { status: 1, pageSize: 999 };

          if (moduleId) {
            // 选了模块：精确过滤到该模块下的仓库
            params.module = moduleId;
          } else if (projectId) {
            // 只选项目：仅过滤直接挂在项目下（无模块）的仓库
            params.project = projectId;
            params.module__isnull = true;
          } else {
            params = undefined;
          }

          return {
            params,
            placeholder: moduleId ? '请选择代码仓库' : (projectId ? '请选择代码仓库（仅项目级）' : '请先选择项目或模块'),
          };
        },
        trigger: (_values, _form) => {
        },
      },
      componentProps: {
        api: getCodeRepositoryList,
        resultField: 'items',
        labelField: 'name',
        valueField: 'id',
        immediate: false,
        showSearch: true,
        filterOption: (input: string, option: { label: string }) =>
          option.label.toLowerCase().includes(input.toLowerCase()),
      },
    },
    {
      component: 'Input',
      fieldName: 'name',
      label: '应用名称',
      rules: z
        .string()
        .min(2, '应用名称至少2个字符')
        .max(50, '应用名称最多50个字符'),
    },
    {
      component: 'Input',
      fieldName: 'code',
      label: '应用编码',
      rules: z
        .string()
        .min(2, '应用编码至少2个字符')
        .max(30, '应用编码最多30个字符')
        .regex(/^[a-zA-Z][a-zA-Z0-9_-]*$/, '编码必须以字母开头，只能包含字母、数字、下划线和横杠'),
    },
    {
      component: 'Select',
      fieldName: 'app_type',
      label: '应用类型',
      rules: z.string({ required_error: '请选择应用类型' }),
      componentProps: {
        options: APP_TYPE_OPTIONS,
        placeholder: '请选择应用类型',
      },
    },
    {
      component: 'Input',
      fieldName: 'code_subpath',
      label: '代码子目录',
      componentProps: {
        placeholder: '仓库内的子目录，如：order-service（可选）',
      },
    },
    {
      component: 'Input',
      fieldName: 'build_command',
      label: '编译命令',
      componentProps: {
        placeholder: '如：mvn clean package 或 npm run build（可选）',
      },
    },
    {
      component: 'Textarea',
      fieldName: 'description',
      label: '应用描述',
      componentProps: {
        maxLength: 200,
        rows: 2,
        showCount: true,
      },
    },
    {
      component: 'Input',
      fieldName: 'git_url',
      label: 'Git仓库地址',
      componentProps: {
        placeholder: '如：git@gitlab.example.com:group/project.git（可选）',
      },
    },
    {
      component: 'Input',
      fieldName: 'build_branch',
      label: '构建分支',
      componentProps: {
        placeholder: '默认构建分支，如：main, master, develop',
      },
      defaultValue: 'main',
    },
    {
      component: 'Input',
      fieldName: 'dockerfile_path',
      label: 'Dockerfile路径',
      componentProps: {
        placeholder: '如：./Dockerfile 或 docker/Dockerfile',
      },
      defaultValue: './Dockerfile',
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
  moduleOptions?: Ref<{ label: string; value: number }[]>,
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
      component: 'Select',
      fieldName: 'module',
      label: '所属模块',
      componentProps: {
        allowClear: true,
        placeholder: '请选择模块',
        options: moduleOptions,
        showSearch: true,
        filterOption: (input: string, option: { label: string }) =>
          option.label.toLowerCase().includes(input.toLowerCase()),
      },
    },
    {
      component: 'Input',
      fieldName: 'name',
      label: '应用名称',
      componentProps: { allowClear: true, placeholder: '请输入应用名称' },
    },
    {
      component: 'Select',
      fieldName: 'app_type',
      label: '应用类型',
      componentProps: {
        allowClear: true,
        options: APP_TYPE_OPTIONS,
      },
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
  onActionClick?: OnActionClickFn<ReleaseApplicationApi.Application>,
): VxeTableGridOptions<ReleaseApplicationApi.Application>['columns'] {
  return [
    {
      type: 'seq',
      title: '序号',
      width: 60,
    },
    {
      field: 'project_name',
      title: '所属项目',
      width: 120,
    },
    {
      field: 'module_name',
      title: '所属模块',
      width: 120,
    },
    {
      field: 'name',
      title: '应用名称',
      minWidth: 150,
    },
    {
      field: 'code',
      title: '应用编码',
      width: 120,
    },
    {
      field: 'app_type_display',
      title: '应用类型',
      width: 100,
    },
    {
      title: 'Jenkins 同步',
      width: 100,
      align: 'center',
      slots: { default: 'jenkins_sync' },
    },
    {
      title: 'Harbor 同步',
      width: 100,
      align: 'center',
      slots: { default: 'harbor_sync' },
    },
    {
      cellRender: { name: 'CellTag' },
      field: 'status',
      title: '状态',
      width: 80,
    },
    {
      field: 'build_branch',
      title: '构建分支',
      width: 100,
    },
    {
      field: 'creator',
      title: '创建人',
      width: 80,
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
      width: 310,
    },
  ];
}
