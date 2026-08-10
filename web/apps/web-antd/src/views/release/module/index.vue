<script lang="ts" setup>
import {
  ACTION_ICON,
  type OnActionClickParams,
  TableAction,
  type VxeTableGridOptions,
} from '#/adapter/vxe-table';
import type { ReleaseModuleApi } from '#/api/release';

import { Page, useVbenModal } from '@vben/common-ui';

import { nextTick, onMounted, ref } from 'vue';

import { message, Tag } from 'ant-design-vue';

import { useRoute, useRouter } from 'vue-router';

import { useVbenVxeGrid } from '#/adapter/vxe-table';
import { deleteModule, getModuleList, getProjectList, syncModuleGitlab } from '#/api/release';
import { $t } from '#/locales';
import { hasPermission } from '#/utils/permission';

import { useColumns, useGridFormSchema, type ModuleColumnOptions } from './data';
import Form from './modules/form.vue';
import ImportGitlabModal from './modules/importGitlabModal.vue';

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

// 项目列表用于筛选
const projectOptions = ref<{ label: string; value: number }[]>([]);

// 加载项目列表
async function loadProjects() {
  const result = await getProjectList({ page: 1, pageSize: 999 });
  const list = Array.isArray(result) ? result : (result?.items || []);
  projectOptions.value = list.map((item: any) => ({
    label: item.name,
    value: item.id,
  }));
}

// 初始化加载项目列表
loadProjects();

const route = useRoute();
const router = useRouter();

// 从查询参数读取 project 并自动填入搜索表单
onMounted(async () => {
  const projectId = route.query.project as string | undefined;
  const autoCreate = route.query.create as string | undefined;

  await nextTick();

  if (projectId) {
    gridApi.formApi.setValues({ project: Number(projectId) });
    gridApi.query();
  }

  // URL 携带 create=1 自动弹出创建表单前，先校验按钮权限，防止无权限用户绕过
  if (autoCreate === '1' && hasPermission('release:module:create')) {
    onCreate(projectId ? Number(projectId) : undefined);
  }
});

/**
 * 编辑模块
 */
function onEdit(row: ReleaseModuleApi.Module) {
  formModalApi.setData(row).open();
}

/**
 * 创建新模块
 */
function onCreate(projectId?: number) {
  const data: any = projectId ? { project: projectId } : null;
  formModalApi.setData(data).open();
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
function goToAppList(row: ReleaseModuleApi.Module) {
  router.push({ path: '/release/application', query: { module: String(row.id) } });
}

function goToRepoList(row: ReleaseModuleApi.Module) {
  router.push({ path: '/release/code-repository', query: { module: String(row.id) } });
}

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
    case 'create-code-repository': {
      router.push({ path: '/release/code-repository', query: { module: String(row.id), project: String(row.project), create: '1' } });
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
    columns: useColumns({ onActionClick, goToAppList, goToRepoList } satisfies ModuleColumnOptions),
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
            pageSize: page?.pageSize,
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
    <ImportModal @success="refreshGrid" />
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
            {
              label: '从 GitLab 导入',
              icon: ACTION_ICON.IMPORT,
              auth: ['release:module:import'],
              onClick: openImportModal,
            },
          ]"
        />
      </template>
      <template #app_count="{ row }">
        <a class="text-primary cursor-pointer" @click="goToAppList(row)">
          {{ row.app_count ?? 0 }}
        </a>
      </template>
      <template #repo_count="{ row }">
        <a class="text-primary cursor-pointer" @click="goToRepoList(row)">
          {{ row.repo_count ?? 0 }}
        </a>
      </template>
      <template #gitlab_status="{ row }">
        <template v-if="row.gitlab_subgroup_id && row.gitlab_subgroup_url">
          <a :href="row.gitlab_subgroup_url" target="_blank" rel="noopener noreferrer">
            已创建
          </a>
        </template>
        <Tag v-else :color="row.gitlab_subgroup_id ? 'success' : 'default'">
          {{ row.gitlab_subgroup_id ? '已创建' : '未创建' }}
        </Tag>
      </template>
      <template #operation="{ row }">
        <TableAction
          :actions="[
            {
              label: '新增仓库',
              auth: ['release:code_repository:create'],
              onClick: () => onActionClick({ code: 'create-code-repository', row }),
            },
            {
              label: '编辑',
              auth: ['release:module:edit'],
              onClick: () => onEdit(row),
            },
            {
              label: '同步GitLab',
              auth: ['release:module:sync-gitlab'],
              onClick: () => onSyncGitlab(row),
            },
            {
              label: '删除',
              auth: ['release:module:delete'],
              danger: true,
              popConfirm: {
                title: $t('ui.actionMessage.deleteConfirm', [row.name]),
                confirm: () => onDelete(row),
              },
            },
          ]"
        />
      </template>
    </Grid>
  </Page>
</template>
