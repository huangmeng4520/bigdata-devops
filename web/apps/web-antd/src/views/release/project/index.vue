<script lang="ts" setup>
import {
  ACTION_ICON,
  type OnActionClickParams,
  TableAction,
  type VxeTableGridOptions,
} from '#/adapter/vxe-table';
import type { ReleaseProjectApi } from '#/api/release';

import { Page, useVbenModal } from '@vben/common-ui';

import { message, Tag } from 'ant-design-vue';

import { useVbenVxeGrid } from '#/adapter/vxe-table';
import { deleteProject, getProjectList, syncProjectGitlab } from '#/api/release';
import { $t } from '#/locales';

import { useColumns, useGridFormSchema } from './data';
import Form from './modules/form.vue';

const [FormModal, formModalApi] = useVbenModal({
  connectedComponent: Form,
  destroyOnClose: false,
});

/**
 * 编辑项目
 */
function onEdit(row: ReleaseProjectApi.Project) {
  formModalApi.setData(row).open();
}

/**
 * 创建新项目
 */
function onCreate() {
  formModalApi.setData(null).open();
}

/**
 * 删除项目
 */
function onDelete(row: ReleaseProjectApi.Project) {
  const hideLoading = message.loading({
    content: $t('ui.actionMessage.deleting', [row.name]),
    duration: 0,
    key: 'action_process_msg',
  });
  deleteProject(row.id)
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
 * 同步GitLab Group
 */
function onSyncGitlab(row: ReleaseProjectApi.Project) {
  const hideLoading = message.loading({
    content: `正在同步 ${row.name} 的 GitLab Group...`,
    duration: 0,
    key: 'action_process_msg',
  });
  syncProjectGitlab(row.id)
    .then(() => {
      message.success({
        content: `${row.name} 的 GitLab Group 同步成功`,
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
}: OnActionClickParams<ReleaseProjectApi.Project>) {
  switch (code) {
    case 'delete': {
      onDelete(row);
      break;
    }
    case 'edit': {
      onEdit(row);
      break;
    }
    case 'sync-gitlab': {
      onSyncGitlab(row);
      break;
    }
  }
}

const [Grid, gridApi] = useVbenVxeGrid({
  formOptions: {
    schema: useGridFormSchema(),
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
          const result = await getProjectList(params);
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
</script>

<template>
  <Page auto-content-height>
    <FormModal @success="refreshGrid" />
    <Grid table-title="项目列表">
      <template #toolbar-tools>
        <TableAction
          :actions="[
            {
              label: $t('ui.actionTitle.create', ['项目']),
              type: 'primary',
              icon: ACTION_ICON.ADD,
              auth: ['release:project:create'],
              onClick: onCreate,
            },
          ]"
        />
      </template>
      <template #gitlab_status="{ row }">
        <Tag :color="row.gitlab_group_id ? 'success' : 'default'">
          {{ row.gitlab_group_id ? '已创建' : '未创建' }}
        </Tag>
      </template>
    </Grid>
  </Page>
</template>
