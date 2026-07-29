<script lang="ts" setup>
import type {
  OnActionClickParams,
  VxeTableGridOptions,
} from '#/adapter/vxe-table';
import type { PipelineTemplateApi } from '#/api/release';

import { Page, useVbenModal } from '@vben/common-ui';
import { Plus } from '@vben/icons';

import { message } from 'ant-design-vue';

import { useVbenVxeGrid } from '#/adapter/vxe-table';
import {
  copyTemplate,
  deleteTemplate,
  exportTemplate,
  getTemplateList,
  importTemplate,
} from '#/api/release';
import { hasPermission } from '#/utils/permission';

import { setOnActionClick, useColumns, useGridFormSchema } from './data';
import Form from './modules/form.vue';
import Versions from './modules/versions.vue';

const [FormModal, formModalApi] = useVbenModal({
  connectedComponent: Form,
  destroyOnClose: false,
});

const [VersionModal, versionModalApi] = useVbenModal({
  connectedComponent: Versions,
  destroyOnClose: false,
});

/**
 * 编辑模板
 */
function onEdit(row: PipelineTemplateApi.Template) {
  formModalApi.setData(row).open();
}

/**
 * 创建新模板
 */
function onCreate() {
  formModalApi.setData(null).open();
}

/**
 * 查看版本
 */
function onVersions(row: PipelineTemplateApi.Template) {
  versionModalApi.setData(row).open();
}

/**
 * 复制模板
 */
function onCopy(row: PipelineTemplateApi.Template) {
  const hideLoading = message.loading({
    content: '正在复制...',
    duration: 0,
  });
  copyTemplate(row.id, {
    name: `${row.name}_copy`,
    code: `${row.code}_copy`,
  })
    .then(() => {
      message.success('复制成功');
      gridApi.query();
    })
    .catch((error) => {
      message.error(error?.message || '复制失败');
    })
    .finally(() => {
      hideLoading();
    });
}

/**
 * 导出模板
 */
function onExport(row: PipelineTemplateApi.Template) {
  const hideLoading = message.loading({
    content: '正在导出...',
    duration: 0,
  });
  exportTemplate(row.id)
    .then((data) => {
      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: 'application/json',
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${row.code}_template.json`;
      a.click();
      URL.revokeObjectURL(url);
      message.success('导出成功');
    })
    .catch(() => {
      message.error('导出失败');
    })
    .finally(() => {
      hideLoading();
    });
}

/**
 * 导入模板
 */
function onImport() {
  const input = document.createElement('input');
  input.type = 'file';
  input.accept = '.json';
  input.addEventListener('change', (e: any) => {
    const file = e.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.addEventListener('load', (event: any) => {
      try {
        const data = JSON.parse(event.target.result);
        const hideLoading = message.loading({
          content: '正在导入...',
          duration: 0,
        });
        importTemplate(data)
          .then(() => {
            message.success('导入成功');
            gridApi.query();
          })
          .catch((error) => {
            message.error(error?.message || '导入失败');
          })
          .finally(() => {
            hideLoading();
          });
      } catch {
        message.error('文件格式错误');
      }
    });
    reader.readAsText(file);
  });
  input.click();
}

/**
 * 删除模板
 */
function onDelete(row: PipelineTemplateApi.Template) {
  const hideLoading = message.loading({
    content: '正在删除...',
    duration: 0,
  });
  deleteTemplate(row.id)
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
function onActionClick({
  row,
  code,
}: OnActionClickParams<PipelineTemplateApi.Template>) {
  switch (code) {
    case 'copy': {
      onCopy(row);
      break;
    }
    case 'delete': {
      onDelete(row);
      break;
    }
    case 'edit': {
      onEdit(row);
      break;
    }
    case 'export': {
      onExport(row);
      break;
    }
    case 'versions': {
      onVersions(row);
      break;
    }
  }
}

// 设置操作回调
setOnActionClick(onActionClick);

const [Grid, gridApi] = useVbenVxeGrid({
  tableTitle: '流水线模板列表',
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
          const result = await getTemplateList({
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
</script>

<template>
  <Page auto-content-height>
    <Grid table-title="流水线模板管理">
      <template #toolbar-tools>
        <a-button
          v-if="hasPermission('release:pipeline_template:create')"
          type="primary"
          @click="onCreate"
        >
          <Plus class="mr-1" />
          创建模板
        </a-button>
        <a-button
          v-if="hasPermission('release:pipeline_template:create')"
          @click="onImport"
        >
          导入模板
        </a-button>
      </template>
    </Grid>
    <FormModal @success="gridApi.query()" />
    <VersionModal @success="gridApi.query()" />
  </Page>
</template>
