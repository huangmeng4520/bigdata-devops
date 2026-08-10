<script lang="ts" setup>
import type { ReleaseApplicationApi } from '#/api/release';

import { computed, ref } from 'vue';

import { useVbenModal } from '@vben/common-ui';

import {
  Button,
  Card,
  Descriptions,
  DescriptionsItem,
  Divider,
  Drawer,
  Empty,
  Form,
  FormItem,
  message,
  Select,
  SelectOption,
  Spin,
  Table,
  Tag,
  Textarea,
} from 'ant-design-vue';

import {
  ENVIRONMENT_OPTIONS,
  getConfigList,
  getSyncStatus,
  generateJenkinsfile,
  generateAndSync,
  syncConfigToJenkins,
  getConfigVersions,
  createConfig,
} from '#/api/release';
import {
  getTemplateList,
  getTemplateVersions,
  type PipelineTemplateApi,
} from '#/api/release/pipelineTemplate';
import type { ApplicationPipelineApi } from '#/api/release';
import { format_datetime } from '#/utils/date';
import {
  VARIABLE_PRIORITY,
  BUILTIN_VARIABLES,
  BUILTIN_VAR_COLUMNS,
} from '../../utils/pipelineBuiltin';

const SYNC_STATUS_COLORS: Record<number, string> = {
  0: 'default', 1: 'processing', 2: 'success', 3: 'error',
};
const SYNC_STATUS_TEXT: Record<number, string> = {
  0: '待同步', 1: '同步中', 2: '已同步', 3: '同步失败',
};

const [Modal, modalApi] = useVbenModal({
  onOpenChange: async (isOpen) => {
    if (isOpen) {
      const data = modalApi.getData<ReleaseApplicationApi.Application>();
      if (data) {
        app.value = data;
        await Promise.all([loadConfigs(), loadTemplates()]);
      }
    } else {
      drawerVisible.value = false;
    }
  },
});

const app = ref<ReleaseApplicationApi.Application | null>(null);
const configs = ref<ApplicationPipelineApi.Config[]>([]);
const loading = ref(false);
const templates = ref<PipelineTemplateApi.Template[]>([]);

const templateOptions = computed(() =>
  templates.value.map((t) => ({
    value: t.id,
    label: `${t.name} (${t.language}${t.framework ? '/' + t.framework : ''})`,
  }))
);

const envWithConfig = computed(() =>
  ENVIRONMENT_OPTIONS.map((env) => ({
    ...env,
    config: configs.value.find((c) => c.environment === env.value) || null,
  }))
);

async function loadConfigs() {
  if (!app.value) return;
  loading.value = true;
  try {
    const result = await getConfigList({ page: 1, application: app.value.id, pageSize: 100 });
    configs.value = result.items || [];
  } catch {
    message.error('加载配置失败');
  } finally {
    loading.value = false;
  }
}

async function loadTemplates(keyword?: string) {
  try {
    const result = await getTemplateList({
      page: 1,
      pageSize: 50,
      status: 1,
      name: keyword || undefined,
    });
    templates.value = (result as any)?.items ?? (Array.isArray(result) ? result : []);
  } catch {
    message.error('加载模板列表失败');
  }
}

// 关联模板远程搜索：用户输入时调用后端按 name 过滤，避免本地分页限制漏掉模板
let templateSearchTimer: ReturnType<typeof setTimeout> | null = null;
function handleTemplateSearch(value: string) {
  if (templateSearchTimer) clearTimeout(templateSearchTimer);
  templateSearchTimer = setTimeout(() => {
    loadTemplates(value);
  }, 300);
}

function getSyncTag(config: ApplicationPipelineApi.Config) {
  // 已同步但配置已变更未重新同步 -> 待重新同步（橙色）
  if (config.jenkins_sync_status === 2 && config.config_dirty) {
    return { color: 'orange', text: '待重新同步' };
  }
  const color = SYNC_STATUS_COLORS[config.jenkins_sync_status] || 'default';
  const text = config.jenkins_sync_status_display || SYNC_STATUS_TEXT[config.jenkins_sync_status] || '未知';
  return { color, text };
}

// ===== Drawer =====
const drawerVisible = ref(false);
const drawerSaving = ref(false);
const drawerEnv = ref<string>('dev');

const drawerForm = ref<{
  template: number | undefined;
  template_version: number | undefined;
  variables: Record<string, any>;
}>({
  template: undefined,
  template_version: undefined,
  variables: {},
});

const templateVersions = ref<PipelineTemplateApi.TemplateVersion[]>([]);

const drawerTitle = computed(() => {
  const envLabel = ENVIRONMENT_OPTIONS.find((o) => o.value === drawerEnv.value)?.label || drawerEnv.value;
  return `${envLabel} - 流水线配置`;
});

const drawerConfig = computed(() =>
  configs.value.find((c) => c.environment === drawerEnv.value) || null
);

const drawerSyncing = ref(false);
const drawerGenerating = ref(false);
const drawerJenkinsfile = ref('');
const drawerVersions = ref<ApplicationPipelineApi.ConfigVersion[]>([]);
const drawerShowVersions = ref(false);

function openDrawer(env: string) {
  drawerEnv.value = env;
  drawerShowVersions.value = false;
  drawerJenkinsfile.value = '';
  drawerVersions.value = [];

  if (drawerConfig.value) {
    drawerForm.value = {
      template: drawerConfig.value.template,
      template_version: drawerConfig.value.template_version,
      variables: drawerConfig.value.variables || {},
    };
    if (drawerConfig.value.template) {
      loadTemplateVersions(drawerConfig.value.template);
    } else {
      templateVersions.value = [];
    }
  } else {
    drawerForm.value = {
      template: undefined,
      template_version: undefined,
      variables: {},
    };
    templateVersions.value = [];
  }
  drawerVisible.value = true;
}

function resetDrawerForm() {
  drawerForm.value = {
    template: undefined,
    template_version: undefined,
    variables: {},
  };
  templateVersions.value = [];
  drawerJenkinsfile.value = '';
  drawerVersions.value = [];
  drawerShowVersions.value = false;
}

async function loadTemplateVersions(templateId: number) {
  try {
    const result = await getTemplateVersions(templateId, { status: 1 });
    templateVersions.value = result.items || [];
  } catch {
    templateVersions.value = [];
  }
}

function handleTemplateChange(value: number | undefined) {
  drawerForm.value.template_version = undefined;
  if (value) {
    loadTemplateVersions(value);
  } else {
    templateVersions.value = [];
  }
}

async function handleSave() {
  if (!app.value) return;
  if (!drawerForm.value.template) {
    message.warning('请选择流水线模板');
    return;
  }
  drawerSaving.value = true;
  try {
    await createConfig({
      application: app.value.id,
      environment: drawerEnv.value,
      template: drawerForm.value.template,
      template_version: drawerForm.value.template_version,
      variables: drawerForm.value.variables,
      is_active: true,
    });
    message.success('保存成功');
    await loadConfigs();
  } catch (error: any) {
    message.error(error?.response?.data?.message || '保存失败');
  } finally {
    drawerSaving.value = false;
  }
}

async function handleGenerate() {
  if (!drawerConfig.value) return;
  drawerGenerating.value = true;
  try {
    const result = await generateJenkinsfile(drawerConfig.value.id);
    drawerJenkinsfile.value = result.content;
    message.success(`Jenkinsfile v${result.version} 已生成`);
    await loadConfigs();
  } catch {
    message.error('生成 Jenkinsfile 失败');
  } finally {
    drawerGenerating.value = false;
  }
}

async function handleGenerateAndSync() {
  if (!drawerConfig.value) return;
  drawerGenerating.value = true;
  try {
    const result = await generateAndSync(drawerConfig.value.id);
    drawerJenkinsfile.value = result.content;
    message.success(result.message || 'Jenkinsfile 已生成，正在同步...');
    pollSyncStatus(drawerConfig.value.id);
    await loadConfigs();
  } catch {
    message.error('操作失败');
  } finally {
    drawerGenerating.value = false;
  }
}

async function handleSync() {
  if (!drawerConfig.value) return;
  drawerSyncing.value = true;
  try {
    const result = await syncConfigToJenkins(drawerConfig.value.id);
    message.success(result.message || '同步任务已提交');
    pollSyncStatus(drawerConfig.value.id);
  } catch {
    message.error('同步失败');
  } finally {
    drawerSyncing.value = false;
  }
}

async function handleViewVersions() {
  if (!drawerConfig.value) return;
  drawerShowVersions.value = true;
  try {
    const result = await getConfigVersions(drawerConfig.value.id, { page: 1, pageSize: 100 });
    drawerVersions.value = result.items || [];
  } catch {
    message.error('加载版本历史失败');
  }
}

async function pollSyncStatus(configId: number, maxAttempts = 10) {
  let attempts = 0;
  const poll = async () => {
    if (attempts >= maxAttempts) return;
    try {
      const result = await getSyncStatus(configId);
      const status = result.data;
      const config = configs.value.find((c) => c.id === configId);
      if (config) {
        config.jenkins_sync_status = status.sync_status;
        config.jenkins_sync_status_display = status.sync_status_display;
        config.jenkins_sync_time = status.sync_time;
        config.jenkins_sync_message = status.sync_message;
        config.jenkins_job_name = status.jenkins_job_name;
        config.config_dirty = status.config_dirty;
      }
      if (status.sync_status === 1) {
        attempts++;
        setTimeout(poll, 2000);
      } else if (status.sync_status === 2) {
        message.success('同步成功');
      } else if (status.sync_status === 3) {
        message.error(`同步失败: ${status.sync_message}`);
      }
    } catch {
      console.error('获取同步状态失败');
    }
  };
  poll();
}

const versionColumns = [
  { title: '版本', dataIndex: 'version', width: 80 },
  { title: '生成人', dataIndex: 'generated_by', width: 100 },
  { title: '生成时间', dataIndex: 'create_time', width: 160 },
  { title: '操作', key: 'action', width: 100 },
];
</script>

<template>
  <Modal :footer="false" :width="800" title="流水线配置管理">
    <Spin :spinning="loading">
      <div v-if="!app" class="p-4"><Empty description="请选择应用" /></div>

      <div v-else>
        <Card size="small" class="mb-4">
          <Descriptions :column="4" size="small">
            <DescriptionsItem label="应用名称">{{ app.name }}</DescriptionsItem>
            <DescriptionsItem label="应用编码">{{ app.code }}</DescriptionsItem>
            <DescriptionsItem label="应用类型">{{ app.app_type_display }}</DescriptionsItem>
            <DescriptionsItem label="构建分支">{{ app.build_branch || 'main' }}</DescriptionsItem>
          </Descriptions>
        </Card>

        <Card
          v-for="item in envWithConfig"
          :key="item.value"
          size="small"
          class="mb-3 cursor-pointer"
          @click="openDrawer(item.value)"
        >
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <span class="font-medium text-base">{{ item.label }}</span>
              <template v-if="item.config">
                <Tag color="green">已配置</Tag>
                <Tag v-if="item.config.template_name" color="blue">{{ item.config.template_name }}</Tag>
                <Tag :color="getSyncTag(item.config).color">{{ getSyncTag(item.config).text }}</Tag>
              </template>
              <Tag v-else color="default">未配置</Tag>
            </div>
            <Button type="primary" size="small" @click.stop="openDrawer(item.value)">
              {{ item.config ? '编辑' : '配置' }}
            </Button>
          </div>
        </Card>
      </div>
    </Spin>

    <Drawer
      v-model:open="drawerVisible"
      :title="drawerTitle"
      placement="right"
      :width="640"
      @close="resetDrawerForm"
    >
      <a-alert type="info" show-icon class="mb-3">
        <template #message>变量替换优先级：应用字段 → 模板默认值 → 用户覆盖</template>
        <template #description>
          <div v-for="p in VARIABLE_PRIORITY" :key="p" style="font-size: 12px;">{{ p }}</div>
        </template>
      </a-alert>
      <a-collapse :bordered="false" ghost class="mb-2">
        <a-collapse-panel key="builtin-vars" header="💡 模板可用的内置变量清单">
          <a-table
            :columns="BUILTIN_VAR_COLUMNS"
            :data-source="BUILTIN_VARIABLES"
            :pagination="false"
            size="small"
            row-key="name"
          />
        </a-collapse-panel>
      </a-collapse>

      <Form layout="vertical">
        <FormItem label="关联模板">
          <Select
            v-model:value="drawerForm.template"
            placeholder="输入模板名称搜索"
            allow-clear show-search
            :options="templateOptions"
            :filter-option="false"
            @search="handleTemplateSearch"
            @change="(val) => handleTemplateChange(val as number | undefined)"
          />
        </FormItem>

        <FormItem v-if="templateVersions.length > 0" label="模板版本">
          <Select v-model:value="drawerForm.template_version" placeholder="选择版本（默认最新）">
            <SelectOption v-for="ver in templateVersions" :key="ver.id" :value="ver.id">
              v{{ ver.version }} {{ ver.is_latest ? '(最新)' : '' }}
            </SelectOption>
          </Select>
        </FormItem>

        <FormItem>
          <Button type="primary" :loading="drawerSaving" @click="handleSave">保存</Button>
        </FormItem>
      </Form>

      <template v-if="drawerConfig">
        <Divider />

        <div class="flex flex-wrap gap-2 mb-4">
          <Button type="primary" :loading="drawerGenerating" @click="handleGenerateAndSync">
            生成并同步
          </Button>
          <Button :loading="drawerGenerating" @click="handleGenerate">
            生成 Jenkinsfile
          </Button>
          <Button
            :loading="drawerSyncing"
            :disabled="drawerConfig.current_version === 0"
            @click="handleSync"
          >
            同步到 Jenkins
          </Button>
          <Button @click="handleViewVersions">
            版本历史
          </Button>
        </div>

        <div v-if="drawerShowVersions && drawerVersions.length > 0" class="mb-4">
          <Table
            :columns="versionColumns"
            :data-source="drawerVersions"
            :pagination="false"
            size="small"
            row-key="id"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'action'">
                <Button type="link" size="small" @click="drawerJenkinsfile = record.content">查看</Button>
              </template>
              <template v-else-if="column.dataIndex === 'create_time'">
                {{ format_datetime(record.create_time) }}
              </template>
            </template>
          </Table>
        </div>

        <div v-if="drawerJenkinsfile">
          <Divider />
          <h4 class="font-medium mb-2">Jenkinsfile 预览</h4>
          <Textarea
            :value="drawerJenkinsfile"
            :auto-size="{ minRows: 8, maxRows: 20 }"
            readonly
            class="font-mono text-sm"
          />
        </div>
      </template>
    </Drawer>
  </Modal>
</template>
