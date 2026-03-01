<script lang="ts" setup>
import {
  ACTION_ICON,
  type OnActionClickParams,
  TableAction,
  type VxeTableGridOptions,
} from '#/adapter/vxe-table';
import type { ReleaseApplicationApi } from '#/api/release';

import { Page, useVbenModal } from '@vben/common-ui';
import { Plus } from '@vben/icons';

import { ref } from 'vue';

import { message, Tag, Tooltip } from 'ant-design-vue';

import { useVbenVxeGrid } from '#/adapter/vxe-table';
import {
  deleteApplication,
  generateConfig,
  getApplicationList,
  getModulesByProject,
  getProjectList,
  getResourceStatus,
  syncResources,
} from '#/api/release';
import { $t } from '#/locales';

import { useColumns, useGridFormSchema } from './data';
import Form from './modules/form.vue';

const [FormModal, formModalApi] = useVbenModal({
  connectedComponent: Form,
  destroyOnClose: false,
});

// 项目列表用于筛选
const projectOptions = ref<{ label: string; value: number }[]>([]);
// 模块列表用于筛选（根据项目动态变化）
const moduleOptions = ref<{ label: string; value: number }[]>([]);
// 当前选中的项目ID
const selectedProjectId = ref<number | undefined>();
// 资源状态缓存
const resourceStatusMap = ref<Record<number, any>>({});

// 加载项目列表
async function loadProjects() {
  const result = await getProjectList({ page_size: 1000 });
  projectOptions.value = (result.items || []).map((item) => ({
    label: item.name,
    value: item.id,
  }));
}

// 加载模块列表
async function loadModules(projectId: number) {
  try {
    const result = await getModulesByProject(projectId);
    moduleOptions.value = (result || []).map((item: any) => ({
      label: item.name,
      value: item.id,
    }));
  } catch {
    moduleOptions.value = [];
  }
}

// 项目变更时重新加载模块
async function onProjectChange(projectId: number) {
  selectedProjectId.value = projectId;
  moduleOptions.value = [];
  if (projectId) {
    await loadModules(projectId);
  }
  // 触发表格刷新
  gridApi.query();
}

// 初始化加载项目列表
loadProjects();

/**
 * 编辑应用
 */
function onEdit(row: ReleaseApplicationApi.Application) {
  formModalApi.setData(row).open();
}

/**
 * 创建新应用
 */
function onCreate() {
  formModalApi.setData(null).open();
}

/**
 * 删除应用
 */
function onDelete(row: ReleaseApplicationApi.Application) {
  const hideLoading = message.loading({
    content: $t('ui.actionMessage.deleting', [row.name]),
    duration: 0,
    key: 'action_process_msg',
  });
  deleteApplication(row.id)
    .then(() => {
      message.success({
        content: $t('ui.actionMessage.deleteSuccess', [row.name]),
        key: 'action_process_msg',
      });
      refreshGrid();
    })
    .catch(() => {
      hideLoading();
    });
}

/**
 * 同步资源
 */
function onSyncResources(row: ReleaseApplicationApi.Application) {
  const hideLoading = message.loading({
    content: `正在同步 ${row.name} 的资源...`,
    duration: 0,
    key: 'action_process_msg',
  });
  syncResources(row.id)
    .then(() => {
      message.success({
        content: `${row.name} 的资源同步成功`,
        key: 'action_process_msg',
      });
      refreshGrid();
    })
    .catch(() => {
      hideLoading();
    });
}

/**
 * 生成配置
 */
function onGenerateConfig(row: ReleaseApplicationApi.Application) {
  const hideLoading = message.loading({
    content: `正在为 ${row.name} 生成配置...`,
    duration: 0,
    key: 'action_process_msg',
  });
  generateConfig(row.id)
    .then(() => {
      message.success({
        content: `${row.name} 的配置生成成功`,
        key: 'action_process_msg',
      });
      refreshGrid();
    })
    .catch(() => {
      hideLoading();
    });
}

/**
 * 表格操作按钮的回调函数
 */
function onActionClick({
  code,
  row,
}: OnActionClickParams<ReleaseApplicationApi.Application>) {
  switch (code) {
    case 'delete': {
      onDelete(row);
      break;
    }
    case 'edit': {
      onEdit(row);
      break;
    }
    case 'sync-resources': {
      onSyncResources(row);
      break;
    }
    case 'generate-config': {
      onGenerateConfig(row);
      break;
    }
  }
}

const [Grid, gridApi] = useVbenVxeGrid({
  formOptions: {
    schema: useGridFormSchema(projectOptions, moduleOptions),
    submitOnChange: true,
  },
  gridEvents: {},
  gridOptions: {
    columns: useColumns(onActionClick),
    height: 'auto',
    keepSource: true,
    pagerConfig: {
      enabled: true,
    },
    proxyConfig: {
      ajax: {
        query: async ({ page }, formValues) => {
          const params = {
            page: page?.currentPage,
            page_size: page?.pageSize,
            ...formValues,
          };
          const result = await getApplicationList(params);
          // 清空资源状态缓存，以便重新加载
          resourceStatusMap.value = {};
          return {
            items: result.items,
            total: result.total,
          };
        },
      },
      response: {
        result: 'items',
        total: 'total',
      },
    },
    toolbarConfig: {
      custom: true,
      export: false,
      refresh: { code: 'query' },
      zoom: true,
    },
  } as VxeTableGridOptions,
});

/**
 * 刷新表格
 */
function refreshGrid() {
  gridApi.query();
}

/**
 * 获取资源状态标签颜色
 */
function getResourceColor(status: string) {
  return status === 'created' ? 'success' : 'default';
}

/**
 * 获取资源状态文本
 */
function getResourceText(status: string) {
  return status === 'created' ? '已创建' : '未创建';
}
</script>

<template>
  <Page auto-content-height>
    <FormModal @success="refreshGrid" />
    <Grid table-title="应用列表">
      <template #toolbar-tools>
        <TableAction
          :actions="[
            {
              label: $t('ui.actionTitle.create', ['应用']),
              type: 'primary',
              icon: ACTION_ICON.ADD,
              auth: ['release:application:create'],
              onClick: onCreate,
            },
          ]"
        />
      </template>
      <template #devops_resources="{ row }">
        <div style="display: flex; gap: 4px; justify-content: center; flex-wrap: wrap;">
          <Tooltip :title="row.gitlab_project_id ? 'GitLab 项目已创建' : 'GitLab 项目未创建'">
            <Tag :color="row.gitlab_project_id ? 'success' : 'default'">
              GitLab
            </Tag>
          </Tooltip>
          <Tooltip :title="row.jenkins_ci_job || row.jenkins_cd_job ? 'Jenkins Job 已创建' : 'Jenkins Job 未创建'">
            <Tag :color="row.jenkins_ci_job || row.jenkins_cd_job ? 'success' : 'default'">
              Jenkins
            </Tag>
          </Tooltip>
          <Tooltip :title="row.harbor_project ? 'Harbor 项目已创建' : 'Harbor 项目未创建'">
            <Tag :color="row.harbor_project ? 'success' : 'default'">
              Harbor
            </Tag>
          </Tooltip>
        </div>
      </template>
    </Grid>
  </Page>
</template>
