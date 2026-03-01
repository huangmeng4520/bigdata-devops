<script lang="ts" setup>
import {
  type OnActionClickParams,
  TableAction,
  type VxeTableGridOptions,
} from '#/adapter/vxe-table';
import type { EnvironmentStrategyApi } from '#/api/release';

import { Page, useVbenModal } from '@vben/common-ui';
import { Plus } from '@vben/icons';

import { message } from 'ant-design-vue';

import { useVbenVxeGrid } from '#/adapter/vxe-table';
import {
  deleteStrategy,
  getStrategyList,
  setDefaultStrategy,
} from '#/api/release';

import { useColumns, useGridFormSchema } from './data';
import Form from './modules/form.vue';

const [FormModal, formModalApi] = useVbenModal({
  connectedComponent: Form,
  destroyOnClose: false,
});

/**
 * 编辑策略
 */
function onEdit(row: EnvironmentStrategyApi.Strategy) {
  formModalApi.setData(row).open();
}

/**
 * 创建新策略
 */
function onCreate() {
  formModalApi.setData(null).open();
}

/**
 * 设为默认
 */
async function onSetDefault(row: EnvironmentStrategyApi.Strategy) {
  try {
    await setDefaultStrategy(row.id);
    message.success('已设为默认策略');
    gridApi.query();
  } catch {
    message.error('操作失败');
  }
}

/**
 * 删除策略
 */
function onDelete(row: EnvironmentStrategyApi.Strategy) {
  const hideLoading = message.loading({
    content: '正在删除...',
    duration: 0,
  });
  deleteStrategy(row.id)
    .then(() => {
      message.success('删除成功');
      gridApi.query();
    })
    .catch(() => {
      message.error('删除失败');
    })
    .finally(() => {
      hideLoading();
    });
}

/**
 * 操作按钮
 */
function onActionClick({ row, code }: OnActionClickParams<EnvironmentStrategyApi.Strategy>) {
  switch (code) {
    case 'edit': {
      onEdit(row);
      break;
    }
    case 'default': {
      onSetDefault(row);
      break;
    }
    case 'delete': {
      onDelete(row);
      break;
    }
  }
}

const [Grid, gridApi] = useVbenVxeGrid({
  tableTitle: '环境策略列表',
  formOptions: {
    schema: useGridFormSchema(),
  },
  gridOptions: {
    columns: useColumns(),
    height: 'auto',
    keepSource: true,
    pagerConfig: {
      enabled: true,
      pageSize: 20,
    },
    proxyConfig: {
      ajax: {
        query: async ({ page }, formValues) => {
          const result = await getStrategyList({
            page: page.currentPage,
            page_size: page.pageSize,
            ...formValues,
          });
          return {
            items: result.items || [],
            total: result.total || 0,
          };
        },
      },
    },
    rowConfig: {
      keyField: 'id',
      isHover: true,
    },
    toolbarConfig: {
      custom: true,
      refresh: true,
      zoom: true,
    },
  } as VxeTableGridOptions,
});

function getActionButtons(row: EnvironmentStrategyApi.Strategy) {
  return [
    {
      code: 'edit',
      text: '编辑',
    },
    {
      code: 'default',
      text: '设为默认',
      disabled: row.is_default,
    },
    {
      code: 'delete',
      text: '删除',
      danger: true,
    },
  ];
}
</script>

<template>
  <Page auto-content-height>
    <Grid table-title="环境策略管理">
      <template #toolbar-tools>
        <a-button type="primary" @click="onCreate">
          <Plus class="mr-1" />
          创建策略
        </a-button>
      </template>
      <template #action="{ row }">
        <TableAction
          :actions="getActionButtons(row)"
          @click="onActionClick"
        />
      </template>
    </Grid>
    <FormModal />
  </Page>
</template>
