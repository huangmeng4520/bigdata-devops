<script lang="ts" setup>
import type {
  OnActionClickParams,
  VxeTableGridOptions,
} from '#/adapter/vxe-table';
import type { CodeRepositoryApi } from '#/api/release/codeRepository';

import { nextTick, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { Page, useVbenModal } from '@vben/common-ui';

import { message, Tag } from 'ant-design-vue';

import { ACTION_ICON, TableAction, useVbenVxeGrid } from '#/adapter/vxe-table';
import {
  deleteCodeRepository,
  getCodeRepositoryList,
  syncGitlab,
} from '#/api/release/codeRepository';
import { $t } from '#/locales';

import { useColumns, useGridFormSchema } from './data';
import Form from './modules/form.vue';
import ImportGitlabModal from './modules/importGitlabModal.vue';

const route = useRoute();
const router = useRouter();

const [FormModal, formModalApi] = useVbenModal({
  connectedComponent: Form,
  destroyOnClose: true,
});

const [ImportModal, importModalApi] = useVbenModal({
  connectedComponent: ImportGitlabModal,
  destroyOnClose: true,
});

function openImportModal() {
  importModalApi.open();
}

onMounted(async () => {
  const moduleId = route.query.module as string | undefined;
  const projectId = route.query.project as string | undefined;
  const autoCreate = route.query.create as string | undefined;

  await nextTick();

  const formValues: Record<string, number> = {};
  if (moduleId) formValues.module = Number(moduleId);
  if (projectId) formValues.project = Number(projectId);
  if (Object.keys(formValues).length > 0) {
    gridApi.formApi.setValues(formValues);
    gridApi.query();
  }

  if (autoCreate === '1') {
    onCreate(
      moduleId ? Number(moduleId) : undefined,
      projectId ? Number(projectId) : undefined,
    );
  }
});

function onEdit(row: CodeRepositoryApi.CodeRepository) {
  formModalApi.setData(row).open();
}

function onCreate(moduleId?: number, projectId?: number) {
  const data: Record<string, number> = {};
  if (moduleId) data.module = moduleId;
  if (projectId) data.project = projectId;
  formModalApi.setData(Object.keys(data).length > 0 ? data : null).open();
}

function onDelete(row: CodeRepositoryApi.CodeRepository) {
  const hideLoading = message.loading({
    content: $t('ui.actionMessage.deleting', [row.name]),
    duration: 0,
    key: 'action_process_msg',
  });
  deleteCodeRepository(row.id)
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

function onSyncGitlab(row: CodeRepositoryApi.CodeRepository) {
  if (row.repository_type !== 'gitlab') {
    message.warning('只有 GitLab 类型的仓库才能同步');
    return;
  }

  const hideLoading = message.loading({
    content: `正在同步 ${row.name} 到 GitLab...`,
    duration: 0,
    key: 'action_process_msg',
  });
  syncGitlab(row.id)
    .then(() => {
      message.success({
        content: `${row.name} 的 GitLab 同步任务已提交`,
        key: 'action_process_msg',
      });
      refreshGrid();
    })
    .catch(() => {
      hideLoading();
    });
}

function goToAppList(row: CodeRepositoryApi.CodeRepository) {
  router.push({
    path: '/release/application',
    query: { code_repository: String(row.id) },
  });
}

function onCreateApplication(row: CodeRepositoryApi.CodeRepository) {
  router.push({
    path: '/release/application',
    query: {
      project: String(row.project),
      module: row.module ? String(row.module) : undefined,
      code_repository: String(row.id),
      create: '1',
    },
  });
}

function onActionClick({
  code,
  row,
}: OnActionClickParams<CodeRepositoryApi.CodeRepository>) {
  switch (code) {
    case 'create-application': {
      onCreateApplication(row);
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
          const result = await getCodeRepositoryList(params);
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

function refreshGrid() {
  gridApi.query();
}
</script>

<template>
  <Page auto-content-height>
    <FormModal @success="refreshGrid" />
    <ImportModal @success="refreshGrid" />
    <Grid table-title="代码仓库列表">
      <template #toolbar-tools>
        <TableAction
          :actions="[
            {
              label: $t('ui.actionTitle.create', ['仓库']),
              type: 'primary',
              icon: ACTION_ICON.ADD,
              auth: ['release:code_repository:create'],
              onClick: onCreate,
            },
            {
              label: '从 GitLab 导入',
              icon: ACTION_ICON.IMPORT,
              auth: ['release:code_repository:import'],
              onClick: openImportModal,
            },
          ]"
        />
      </template>
      <template #repository_type="{ row }">
        <Tag
          :color="
            row.repository_type === 'gitlab'
              ? 'blue'
              : row.repository_type === 'github'
                ? 'green'
                : 'orange'
          "
        >
          {{ row.repository_type_display || row.repository_type }}
        </Tag>
      </template>
      <template #status="{ row }">
        <Tag :color="row.status === 1 ? 'success' : 'default'">
          {{ row.status === 1 ? '启用' : '禁用' }}
        </Tag>
      </template>
      <template #app_count="{ row }">
        <a class="text-primary cursor-pointer" @click="goToAppList(row)">
          {{ row.app_count ?? 0 }}
        </a>
      </template>
      <template #operation="{ row }">
        <TableAction
          :actions="[
            {
              label: '新建应用',
              auth: ['release:application:create'],
              onClick: () => onCreateApplication(row),
            },
            {
              label: '同步',
              auth: ['release:code_repository:sync-gitlab'],
              onClick: () => onSyncGitlab(row),
            },
            {
              label: '编辑',
              auth: ['release:code_repository:update'],
              onClick: () => onEdit(row),
            },
            {
              label: '删除',
              danger: true,
              auth: ['release:code_repository:delete'],
              onClick: () => onDelete(row),
            },
          ]"
        />
      </template>
      <template #git_url="{ row }">
        <div class="flex flex-col gap-1 text-xs">
          <div
            v-if="row.git_url"
            class="max-w-72 truncate"
            :title="row.git_url"
          >
            <span class="mr-1 text-gray-400">SSH:</span>
            <code class="text-primary">{{ row.git_url }}</code>
          </div>
          <div
            v-if="row.git_http_url"
            class="max-w-72 truncate"
            :title="row.git_http_url"
          >
            <span class="mr-1 text-gray-400">HTTP:</span>
            <a
              :href="row.git_http_url"
              target="_blank"
              rel="noopener noreferrer"
              class="text-primary"
            >
              {{ row.git_http_url }}
            </a>
          </div>
          <span v-if="!row.git_url && !row.git_http_url" class="text-gray-400">-</span>
        </div>
      </template>
    </Grid>
  </Page>
</template>
