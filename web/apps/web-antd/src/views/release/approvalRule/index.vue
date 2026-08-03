<script lang="ts" setup>
import type {
  OnActionClickParams,
  VxeTableGridOptions,
} from '#/adapter/vxe-table';
import type { ApprovalRuleApi } from '#/api/release';

import { Page, useVbenModal } from '@vben/common-ui';
import { Plus } from '@vben/icons';

import { Button, message } from 'ant-design-vue';

import { TableAction, useVbenVxeGrid } from '#/adapter/vxe-table';
import { deleteApprovalRule, getApprovalRules } from '#/api/release';
import { hasPermission } from '#/utils/permission';

import { useColumns, useGridFormSchema } from './data';
import Form from './modules/form.vue';

const [FormModal, formModalApi] = useVbenModal({
  connectedComponent: Form,
  destroyOnClose: false,
});

/**
 * 编辑审批规则
 */
function onEdit(row: ApprovalRuleApi.ApprovalRule) {
  formModalApi.setData(row).open();
}

/**
 * 创建审批规则
 */
function onCreate() {
  formModalApi.setData(null).open();
}

/**
 * 删除审批规则
 */
function onDelete(row: ApprovalRuleApi.ApprovalRule) {
  const hideLoading = message.loading({
    content: '正在删除...',
    duration: 0,
  });
  deleteApprovalRule(row.id)
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
 * 操作按钮点击
 */
function onActionClick({
  row,
  code,
}: OnActionClickParams<ApprovalRuleApi.ApprovalRule>) {
  switch (code) {
    case 'delete': {
      onDelete(row);
      break;
    }
    case 'edit': {
      onEdit(row);
      break;
    }
  }
}

const [Grid, gridApi] = useVbenVxeGrid({
  tableTitle: '审批规则列表',
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
          const result = await getApprovalRules({
            page: page.currentPage,
            pageSize: page.pageSize,
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

function getActionButtons(row: ApprovalRuleApi.ApprovalRule) {
  return [
    {
      code: 'edit',
      label: '编辑',
      auth: ['release:approval_rule:edit'],
      onClick: () => onEdit(row),
    },
    {
      code: 'delete',
      label: '删除',
      danger: true,
      auth: ['release:approval_rule:delete'],
      onClick: () => onDelete(row),
    },
  ];
}
</script>

<template>
  <Page auto-content-height>
    <Grid table-title="审批规则管理">
      <template #toolbar-tools>
        <Button
          v-if="hasPermission('release:approval_rule:create')"
          type="primary"
          @click="onCreate"
        >
          <Plus class="mr-1" />
          创建规则
        </Button>
      </template>
      <template #action="{ row }">
        <TableAction :actions="getActionButtons(row)" @click="onActionClick" />
      </template>
    </Grid>
    <FormModal />
  </Page>
</template>
