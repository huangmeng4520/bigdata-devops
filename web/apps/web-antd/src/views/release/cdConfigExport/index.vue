<script lang="ts" setup>
import {
  type OnActionClickParams,
  TableAction,
  type VxeTableGridOptions,
} from '#/adapter/vxe-table';
import type { CDConfigExportApi } from '#/api/release';

import { Page, useVbenModal } from '@vben/common-ui';

import { message } from 'ant-design-vue';

import { useVbenVxeGrid } from '#/adapter/vxe-table';
import {
  deleteExport,
  getExportList,
  downloadExport,
} from '#/api/release';

import { useColumns, useGridFormSchema } from './data';
import Detail from './modules/detail.vue';

const [DetailModal, detailModalApi] = useVbenModal({
  connectedComponent: Detail,
  destroyOnClose: false,
});

/**
 * 查看详情
 */
function onView(row: CDConfigExportApi.Export) {
  detailModalApi.setData(row).open();
}

/**
 * 下载
 */
async function onDownload(row: CDConfigExportApi.Export) {
  try {
    const result = await downloadExport(row.id);
    // 创建下载链接
    const blob = new Blob([result.content], { type: 'text/plain' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${row.application_name}-${row.environment}-v${row.config_version}.${result.format === 'jenkinsfile' ? 'groovy' : result.format}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
    message.success('下载成功');
    gridApi.query();
  } catch {
    message.error('下载失败');
  }
}

/**
 * 复制内容
 */
async function onCopy(row: CDConfigExportApi.Export) {
  try {
    const result = await downloadExport(row.id);
    await navigator.clipboard.writeText(result.content);
    message.success('已复制到剪贴板');
  } catch {
    message.error('复制失败');
  }
}

/**
 * 删除
 */
function onDelete(row: CDConfigExportApi.Export) {
  const hideLoading = message.loading({
    content: '正在删除...',
    duration: 0,
  });
  deleteExport(row.id)
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
function onActionClick({ row, code }: OnActionClickParams<CDConfigExportApi.Export>) {
  switch (code) {
    case 'view': {
      onView(row);
      break;
    }
    case 'download': {
      onDownload(row as CDConfigExportApi.Export);
      break;
    }
    case 'copy': {
      onCopy(row as CDConfigExportApi.Export);
      break;
    }
    case 'delete': {
      onDelete(row as CDConfigExportApi.Export);
      break;
    }
  }
}

const [Grid, gridApi] = useVbenVxeGrid({
  tableTitle: 'CD配置导出记录',
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
          const result = await getExportList({
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

function getActionButtons(_row: CDConfigExportApi.Export) {
  return [
    {
      code: 'view',
      text: '查看',
    },
    {
      code: 'download',
      text: '下载',
    },
    {
      code: 'copy',
      text: '复制',
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
    <Grid table-title="CD配置导出历史">
      <template #action="{ row }">
        <TableAction
          :actions="getActionButtons(row)"
          @click="onActionClick"
        />
      </template>
    </Grid>
    <DetailModal />
  </Page>
</template>
