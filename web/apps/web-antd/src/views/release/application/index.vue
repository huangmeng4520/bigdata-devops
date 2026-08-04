<script lang="ts" setup>
import {
  ACTION_ICON,
  type OnActionClickParams,
  TableAction,
  type VxeTableGridOptions,
} from '#/adapter/vxe-table';
import type { ReleaseApplicationApi } from '#/api/release';

import { Page, useVbenModal } from '@vben/common-ui';

import { nextTick, onMounted, ref } from 'vue';

import { useRoute } from 'vue-router';

import { Button, Dropdown, Menu, MenuItem, message, Popconfirm, Tag, Tooltip } from 'ant-design-vue';

import { useVbenVxeGrid } from '#/adapter/vxe-table';
import {
  deleteApplication,
  getApplicationList,
  getModuleList,
  getProjectList,
  syncHarbor,
  syncApplicationToJenkins,
} from '#/api/release';
import { $t } from '#/locales';
import { hasPermission } from '#/utils/permission';

import { useColumns, useGridFormSchema } from './data';
import Form from './modules/form.vue';
import ReleaseModal from './modules/ReleaseModal.vue';
import PipelineConfigModal from './modules/PipelineConfigModal.vue';

const [FormModal, formModalApi] = useVbenModal({
  connectedComponent: Form,
  destroyOnClose: true,
});

const [ReleaseModalComp, releaseModalApi] = useVbenModal({
  connectedComponent: ReleaseModal,
  destroyOnClose: true,
});

const [PipelineConfigModalComp, pipelineConfigModalApi] = useVbenModal({
  connectedComponent: PipelineConfigModal,
  destroyOnClose: true,
});

// 项目列表用于筛选
const projectOptions = ref<{ label: string; value: number }[]>([]);
// 模块列表用于筛选（根据项目动态变化）
const moduleOptions = ref<{ label: string; value: number }[]>([]);

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

// 加载模块列表
async function loadModules(projectId?: number) {
  const params: Record<string, any> = { page: 1, pageSize: 999, status: 1 };
  if (projectId) params.project = projectId;
  const result = await getModuleList(params);
  const list = Array.isArray(result) ? result : (result?.items || []);
  moduleOptions.value = list.map((item: any) => ({
    label: item.name,
    value: item.id,
  }));
}

// 初始加载所有模块
loadModules();

const route = useRoute();

onMounted(async () => {
  const projectId = route.query.project as string | undefined;
  const moduleId = route.query.module as string | undefined;
  const codeRepoId = route.query.code_repository as string | undefined;
  const autoCreate = route.query.create as string | undefined;

  await nextTick();

  const formValues: Record<string, number> = {};
  if (projectId) formValues.project = Number(projectId);
  if (moduleId) formValues.module = Number(moduleId);
  if (codeRepoId) formValues.code_repository = Number(codeRepoId);
  if (Object.keys(formValues).length > 0) {
    gridApi.formApi.setValues(formValues);
    gridApi.query();
  }

  if (autoCreate === '1') {
    onCreate(
      projectId ? Number(projectId) : undefined,
      moduleId ? Number(moduleId) : undefined,
      codeRepoId ? Number(codeRepoId) : undefined,
    );
  }
});

/**
 * 编辑应用
 */
function onEdit(row: ReleaseApplicationApi.Application) {
  formModalApi.setData(row).open();
}

/**
 * 创建新应用
 */
function onCreate(projectId?: number, moduleId?: number, codeRepoId?: number) {
  const data: Record<string, number> = {};
  if (projectId) data.project = projectId;
  if (moduleId) data.module = moduleId;
  if (codeRepoId) data.code_repository = codeRepoId;
  formModalApi.setData(Object.keys(data).length > 0 ? data : null).open();
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
 * 同步 Harbor
 */
function onSyncHarbor(row: ReleaseApplicationApi.Application) {
  const hideLoading = message.loading({
    content: `正在同步 ${row.name} 的 Harbor 资源...`,
    duration: 0,
    key: 'action_process_msg',
  });
  syncHarbor(row.id, false)
    .then(() => {
      message.success({
        content: `${row.name} 的 Harbor 同步任务已提交`,
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
  const hideLoading = message.loading({
    content: `正在同步 ${row.name} 的 Pipeline 配置到 Jenkins...`,
    duration: 0,
    key: 'action_process_msg',
  });
  syncApplicationToJenkins(row.id)
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
    case 'sync-harbor': {
      onSyncHarbor(row);
      break;
    }
    case 'sync-jenkins': {
      onSyncJenkins(row);
      break;
    }
    case 'pipeline-config': {
      onPipelineConfig(row);
      break;
    }
    case 'release': {
      onRelease(row);
      break;
    }
  }
}

/**
 * 发布应用
 */
function onRelease(row: ReleaseApplicationApi.Application) {
  releaseModalApi.setData(row).open();
}

/**
 * 流水线配置
 */
function onPipelineConfig(row: ReleaseApplicationApi.Application) {
  pipelineConfigModalApi.setData(row).open();
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
            pageSize: page?.pageSize,
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

// Jenkins 同步状态颜色（应用级：0待同步/1同步中/2已同步/3同步失败/4待重新同步/5未配置）
const SYNC_STATUS_COLORS: Record<number, string> = {
  0: 'default',
  1: 'processing',
  2: 'success',
  3: 'error',
  4: 'orange',
  5: 'default',
};

const SYNC_STATUS_TEXT: Record<number, string> = {
  0: '待同步',
  1: '同步中',
  2: '已同步',
  3: '同步失败',
  4: '待重新同步',
  5: '未配置',
};

// Harbor 同步状态颜色
const HARBOR_SYNC_STATUS_COLORS: Record<number, string> = {
  0: 'default',
  1: 'processing',
  2: 'success',
  3: 'error',
};

const HARBOR_SYNC_STATUS_TEXT: Record<number, string> = {
  0: '待同步',
  1: '同步中',
  2: '已同步',
  3: '同步失败',
};
</script>

<template>
  <Page auto-content-height>
    <FormModal @success="refreshGrid" />
    <ReleaseModalComp @success="refreshGrid" />
    <PipelineConfigModalComp @success="refreshGrid" />
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

      <!-- Jenkins 同步状态 -->
      <template #jenkins_sync="{ row }">
        <Tooltip>
          <template #title>
            <div v-if="row.pipeline_sync_summary && row.pipeline_sync_summary.length">
              <div v-for="s in row.pipeline_sync_summary" :key="s.environment">
                {{ s.environment_display }}：{{ s.config_dirty ? '待重新同步' : s.jenkins_sync_status_display }}
              </div>
            </div>
            <div v-else>未配置流水线</div>
          </template>
          <Tag :color="SYNC_STATUS_COLORS[row.jenkins_sync_status]">
            {{ SYNC_STATUS_TEXT[row.jenkins_sync_status] }}
          </Tag>
        </Tooltip>
      </template>

      <!-- Harbor 同步状态 -->
      <template #harbor_sync="{ row }">
        <Tooltip :title="row.harbor_sync_message || HARBOR_SYNC_STATUS_TEXT[row.harbor_sync_status]">
          <Tag :color="HARBOR_SYNC_STATUS_COLORS[row.harbor_sync_status]">
            {{ HARBOR_SYNC_STATUS_TEXT[row.harbor_sync_status] }}
          </Tag>
        </Tooltip>
      </template>

      <!-- 操作列 -->
      <template #operation="{ row }">
        <div class="flex gap-1 flex-nowrap">
          <Button
            v-if="hasPermission('release:application:release')"
            type="primary" size="small"
            @click="onActionClick({ code: 'release', row })"
          >发布</Button>
          <Button
            v-if="hasPermission('release:application:update')"
            size="small"
            @click="onActionClick({ code: 'edit', row })"
          >编辑</Button>
          <Button
            v-if="hasPermission('release:application:sync-jenkins')"
            type="primary" size="small"
            @click="onActionClick({ code: 'pipeline-config', row })"
          >流水线配置</Button>
          <Dropdown v-if="hasPermission('release:application:sync-jenkins') || hasPermission('release:application:sync-harbor')">
            <Button size="small">更多 ···</Button>
            <template #overlay>
              <Menu>
                <MenuItem v-if="hasPermission('release:application:sync-jenkins')" key="sync-jenkins" @click="onActionClick({ code: 'sync-jenkins', row })">同步 Jenkins</MenuItem>
                <MenuItem v-if="hasPermission('release:application:sync-harbor')" key="sync-harbor" @click="onActionClick({ code: 'sync-harbor', row })">Harbor</MenuItem>
              </Menu>
            </template>
          </Dropdown>
          <Popconfirm
            :title="$t('ui.actionTitle.delete', ['应用'])"
            @confirm="onActionClick({ code: 'delete', row })"
          >
            <template #description>
              <div class="truncate">{{ $t('ui.actionMessage.deleteConfirm', [row.name]) }}</div>
            </template>
            <Button v-if="hasPermission('release:application:delete')" danger size="small">删除</Button>
          </Popconfirm>
        </div>
      </template>
    </Grid>
  </Page>
</template>
