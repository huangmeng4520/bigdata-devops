<script lang="ts" setup>
import {
  ACTION_ICON,
  type OnActionClickParams,
  TableAction,
  type VxeTableGridOptions,
} from '#/adapter/vxe-table';
import type { ReleaseApplicationApi } from '#/api/release';

import { Page, useVbenModal } from '@vben/common-ui';

import { ref } from 'vue';

import { message, Tag, Tooltip } from 'ant-design-vue';

import { useVbenVxeGrid } from '#/adapter/vxe-table';
import {
  deleteApplication,
  getApplicationList,
  getProjectList,
  syncResources,
  syncToJenkins,
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

// 加载项目列表
async function loadProjects() {
  const result = await getProjectList({ page_size: 1000 });
  projectOptions.value = (result.items || []).map((item) => ({
    label: item.name,
    value: item.id,
  }));
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
 * 同步到 Jenkins
 */
function onSyncJenkins(row: ReleaseApplicationApi.Application) {
  if (!row.ci_template && !row.cd_template) {
    message.warning('请先在应用编辑中关联 CI 或 CD 模板');
    return;
  }

  const hideLoading = message.loading({
    content: `正在同步 ${row.name} 的 CI/CD 配置到 Jenkins...`,
    duration: 0,
    key: 'action_process_msg',
  });
  syncToJenkins(row.id)
    .then((res) => {
      hideLoading();
      message.success({
        content: res.message || '同步任务已提交',
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
    case 'sync-jenkins': {
      onSyncJenkins(row);
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

// Jenkins 同步状态颜色
const SYNC_STATUS_COLORS: Record<number, string> = {
  0: 'default',
  1: 'processing',
  2: 'success',
  3: 'error',
};

const SYNC_STATUS_TEXT: Record<number, string> = {
  0: '待同步',
  1: '同步中',
  2: '已同步',
  3: '同步失败',
};
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

      <!-- CI/CD 模板状态 -->
      <template #cicd_templates="{ row }">
        <div style="display: flex; gap: 4px; justify-content: center; flex-wrap: wrap;">
          <Tooltip :title="row.ci_template_name ? `CI: ${row.ci_template_name}` : '未配置 CI 模板'">
            <Tag :color="row.ci_template_name ? 'blue' : 'default'">
              CI
            </Tag>
          </Tooltip>
          <Tooltip :title="row.cd_template_name ? `CD: ${row.cd_template_name}` : '未配置 CD 模板'">
            <Tag :color="row.cd_template_name ? 'green' : 'default'">
              CD
            </Tag>
          </Tooltip>
        </div>
      </template>

      <!-- Jenkins 同步状态 -->
      <template #jenkins_sync="{ row }">
        <Tooltip :title="row.jenkins_sync_message || SYNC_STATUS_TEXT[row.jenkins_sync_status]">
          <Tag :color="SYNC_STATUS_COLORS[row.jenkins_sync_status]">
            {{ SYNC_STATUS_TEXT[row.jenkins_sync_status] }}
          </Tag>
        </Tooltip>
      </template>

      <!-- DevOps 资源状态 -->
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
