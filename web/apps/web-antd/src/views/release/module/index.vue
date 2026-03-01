<script lang="ts" setup>
import {
  ACTION_ICON,
  type OnActionClickParams,
  TableAction,
  type VxeTableGridOptions,
} from '#/adapter/vxe-table';
import type { ReleaseModuleApi } from '#/api/release';

import { Page, useVbenModal } from '@vben/common-ui';
import { Plus } from '@vben/icons';

import { ref } from 'vue';

import { message, Tag } from 'ant-design-vue';

import { useVbenVxeGrid } from '#/adapter/vxe-table';
import { deleteModule, getModuleList, getProjectList, syncModuleGitlab } from '#/api/release';
import { $t } from '#/locales';

import { useColumns, useGridFormSchema } from './data';
import Form from './modules/form.vue';

const [FormModal, formModalApi] = useVbenModal({
  connectedComponent: Form,
  destroyOnClose: false,
});

// 项目列表用于筛选
const projectOptions = ref<{ label: string; value: number }[]>([]);

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
 * 编辑模块
 */
function onEdit(row: ReleaseModuleApi.Module) {
  formModalApi.setData(row).open();
}

/**
 * 创建新模块
 */
function onCreate() {
  formModalApi.setData(null).open();
}

/**
 * 删除模块
 */
function onDelete(row: ReleaseModuleApi.Module) {
  const hideLoading = message.loading({
    content: $t('ui.actionMessage.deleting', [row.name]),
    duration: 0,
    key: 'action_process_msg',
  });
  deleteModule(row.id)
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
 * 同步GitLab Subgroup
 */
function onSyncGitlab(row: ReleaseModuleApi.Module) {
  const hideLoading = message.loading({
    content: `正在同步 ${row.name} 的 GitLab Subgroup...`,
    duration: 0,
    key: 'action_process_msg',
  });
  syncModuleGitlab(row.id)
    .then(() => {
      message.success({
        content: `${row.name} 的 GitLab Subgroup 同步成功`,
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
}: OnActionClickParams<ReleaseModuleApi.Module>) {
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
    schema: useGridFormSchema(projectOptions),
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
          const result = await getModuleList(params);
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
    <Grid table-title="模块列表">
      <template #toolbar-tools>
        <TableAction
          :actions="[
            {
              label: $t('ui.actionTitle.create', ['模块']),
              type: 'primary',
              icon: ACTION_ICON.ADD,
              auth: ['release:module:create'],
              onClick: onCreate,
            },
          ]"
        />
      </template>
      <template #gitlab_status="{ row }">
        <Tag :color="row.gitlab_subgroup_id ? 'success' : 'default'">
          {{ row.gitlab_subgroup_id ? '已创建' : '未创建' }}
        </Tag>
      </template>
    </Grid>
  </Page>
</template>
