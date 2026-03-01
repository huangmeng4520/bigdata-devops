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
  Empty,
  Form,
  FormItem,
  message,
  Select,
  SelectOption,
  Space,
  Spin,
  Tag,
  Tabs,
  TabPane,
  Table,
  Textarea,
  Tooltip,
} from 'ant-design-vue';

import {
  CONFIG_TYPE_OPTIONS,
  ENVIRONMENT_OPTIONS,
  getConfigList,
  getSyncStatus,
  generateJenkinsfile,
  generateAndSync,
  syncToJenkins as syncPipelineConfigToJenkins,
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

// 同步状态颜色映射
const SYNC_STATUS_COLORS: Record<number, string> = {
  0: 'default',
  1: 'processing',
  2: 'success',
  3: 'error',
};

const SYNC_STATUS_TEXT: Record<number, string> = {
  0: '待同步',
  1: '同步中',
  2: '已同步',
  3: '同步失败',
};

const [Modal, modalApi] = useVbenModal({
  onOpenChange: async (isOpen) => {
    if (isOpen) {
      const data = modalApi.getData<ReleaseApplicationApi.Application>();
      if (data) {
        app.value = data;
        await loadConfigs();
        await loadTemplates();
      }
    } else {
      // 关闭时重置
      showCreateForm.value = false;
      resetCreateForm();
    }
  },
});

const app = ref<ReleaseApplicationApi.Application | null>(null);
const configs = ref<ApplicationPipelineApi.Config[]>([]);
const loading = ref(false);
const syncing = ref<number | null>(null);
const generating = ref<number | null>(null);
const activeConfig = ref<ApplicationPipelineApi.Config | null>(null);
const jenkinsfileContent = ref('');
const versions = ref<ApplicationPipelineApi.ConfigVersion[]>([]);
const showVersionHistory = ref(false);

// 创建配置相关
const showCreateForm = ref(false);
const createLoading = ref(false);
const createFormState = ref<{
  config_type: 'ci' | 'cd';
  environment: string;
  template: number | undefined;
  template_version: number | undefined;
  custom_content: string;
  variables: Record<string, any>;
}>({
  config_type: 'ci',
  environment: 'dev',
  template: undefined,
  template_version: undefined,
  custom_content: '',
  variables: {},
});
const templates = ref<PipelineTemplateApi.Template[]>([]);
const templateVersions = ref<PipelineTemplateApi.TemplateVersion[]>([]);
const activeTab = ref<'ci' | 'cd'>('ci');

// 计算属性：按配置类型分组
const ciConfigs = computed(() => configs.value.filter((c: ApplicationPipelineApi.Config) => c.config_type === 'ci'));
const cdConfigs = computed(() => configs.value.filter((c: ApplicationPipelineApi.Config) => c.config_type === 'cd'));

// 根据当前 Tab 筛选模板
const filteredTemplates = computed(() => {
  return templates.value.filter((t: PipelineTemplateApi.Template) => t.template_type === activeTab.value);
});

// 加载配置列表
async function loadConfigs() {
  if (!app.value) return;

  loading.value = true;
  try {
    const result = await getConfigList({
      application: app.value.id,
      page_size: 100,
    });
    configs.value = result.items || [];
  } catch (error) {
    console.error('加载配置失败:', error);
    message.error('加载配置失败');
  } finally {
    loading.value = false;
  }
}

// 加载模板列表
async function loadTemplates() {
  try {
    const result = await getTemplateList({ page_size: 100, status: 1 });
    templates.value = result.items || [];
  } catch (error) {
    console.error('加载模板列表失败:', error);
  }
}

// 加载模板版本
async function loadTemplateVersions(templateId: number) {
  try {
    const result = await getTemplateVersions(templateId, { status: 1 });
    templateVersions.value = result.items || [];
  } catch (error) {
    console.error('加载模板版本失败:', error);
    templateVersions.value = [];
  }
}

// 模板选择变化
function handleTemplateChange(value: number | undefined) {
  createFormState.value.template_version = undefined;
  const templateId = typeof value === 'number' ? value : undefined;
  if (templateId) {
    loadTemplateVersions(templateId);
  } else {
    templateVersions.value = [];
  }
}

// Select 组件的 filter-option 函数
function filterOption(input: string, option?: { label?: string }) {
  return option?.label?.toLowerCase().includes(input.toLowerCase()) ?? false;
}

// Tab 切换时重置创建表单类型
function onTabChange(key: string | number) {
  activeTab.value = key as 'ci' | 'cd';
  createFormState.value.config_type = key as 'ci' | 'cd';
  createFormState.value.template = undefined;
  createFormState.value.template_version = undefined;
  templateVersions.value = [];
}

// 重置创建表单
function resetCreateForm() {
  createFormState.value = {
    config_type: activeTab.value,
    environment: 'dev',
    template: undefined,
    template_version: undefined,
    custom_content: '',
    variables: {},
  };
  templateVersions.value = [];
}

// 创建配置
async function handleCreateConfig() {
  if (!app.value) return;

  // 验证
  if (!createFormState.value.template && !createFormState.value.custom_content) {
    message.warning('请选择模板或填写自定义内容');
    return;
  }

  createLoading.value = true;
  try {
    await createConfig({
      application: app.value.id,
      config_type: createFormState.value.config_type,
      environment: createFormState.value.environment,
      template: createFormState.value.template,
      template_version: createFormState.value.template_version,
      custom_content: createFormState.value.custom_content || undefined,
      variables: createFormState.value.variables,
      is_active: true,
    });
    message.success('配置创建成功');
    showCreateForm.value = false;
    resetCreateForm();
    await loadConfigs();
  } catch (error: any) {
    console.error('创建配置失败:', error);
    message.error(error?.response?.data?.message || '创建配置失败');
  } finally {
    createLoading.value = false;
  }
}

// 获取同步状态标签
function getSyncTag(config: ApplicationPipelineApi.Config) {
  const color = SYNC_STATUS_COLORS[config.jenkins_sync_status] || 'default';
  const text = config.jenkins_sync_status_display || SYNC_STATUS_TEXT[config.jenkins_sync_status] || '未知';
  return { color, text };
}

// 同步到 Jenkins
async function handleSync(config: ApplicationPipelineApi.Config) {
  syncing.value = config.id;
  try {
    const result = await syncPipelineConfigToJenkins(config.id);
    message.success(result.message || '同步任务已提交');
    pollSyncStatus(config.id);
  } catch (error) {
    console.error('同步失败:', error);
    message.error('同步失败');
  } finally {
    syncing.value = null;
  }
}

// 生成并同步（一键操作）
async function handleGenerateAndSync(config: ApplicationPipelineApi.Config) {
  generating.value = config.id;
  try {
    const result = await generateAndSync(config.id);
    message.success(result.message || 'Jenkinsfile 已生成，正在同步...');
    jenkinsfileContent.value = result.content;
    pollSyncStatus(config.id);
  } catch (error) {
    console.error('生成并同步失败:', error);
    message.error('操作失败');
  } finally {
    generating.value = null;
  }
}

// 生成 Jenkinsfile
async function handleGenerate(config: ApplicationPipelineApi.Config) {
  generating.value = config.id;
  try {
    const result = await generateJenkinsfile(config.id);
    jenkinsfileContent.value = result.content;
    message.success(`Jenkinsfile v${result.version} 已生成`);
    await loadConfigs();
  } catch (error) {
    console.error('生成失败:', error);
    message.error('生成 Jenkinsfile 失败');
  } finally {
    generating.value = null;
  }
}

// 轮询同步状态
async function pollSyncStatus(configId: number, maxAttempts = 10) {
  let attempts = 0;
  const poll = async () => {
    if (attempts >= maxAttempts) return;

    try {
      const result = await getSyncStatus(configId);
      const status = result.data;

      const config = configs.value.find((c: ApplicationPipelineApi.Config) => c.id === configId);
      if (config) {
        config.jenkins_sync_status = status.sync_status;
        config.jenkins_sync_status_display = status.sync_status_display;
        config.jenkins_sync_time = status.sync_time;
        config.jenkins_sync_message = status.sync_message;
        config.jenkins_job_name = status.jenkins_job_name;
      }

      if (status.sync_status === 1) {
        attempts++;
        setTimeout(poll, 2000);
      } else if (status.sync_status === 2) {
        message.success('同步成功');
      } else if (status.sync_status === 3) {
        message.error(`同步失败: ${status.sync_message}`);
      }
    } catch (error) {
      console.error('获取同步状态失败:', error);
    }
  };

  poll();
}

// 查看版本历史
async function handleViewVersions(config: ApplicationPipelineApi.Config) {
  activeConfig.value = config;
  showVersionHistory.value = true;

  try {
    const result = await getConfigVersions(config.id);
    versions.value = result.items || [];
  } catch (error) {
    console.error('加载版本历史失败:', error);
    message.error('加载版本历史失败');
  }
}

// 版本历史表格列
const versionColumns = [
  { title: '版本', dataIndex: 'version', width: 80 },
  { title: '生成人', dataIndex: 'generated_by', width: 100 },
  { title: '生成时间', dataIndex: 'create_time', width: 160 },
  { title: '操作', key: 'action', width: 100 },
];

// 环境显示
function getEnvironmentDisplay(env: string) {
  const option = ENVIRONMENT_OPTIONS.find((o: { value: string; label: string }) => o.value === env);
  return option?.label || env;
}

// 配置类型显示
function getConfigTypeDisplay(type: string) {
  const option = CONFIG_TYPE_OPTIONS.find((o: { value: string; label: string }) => o.value === type);
  return option?.label || type;
}
</script>

<template>
  <Modal
    :footer="false"
    :width="1000"
    title="流水线配置管理"
  >
    <Spin :spinning="loading">
      <div v-if="!app" class="p-4">
        <Empty description="请选择应用" />
      </div>

      <div v-else class="pipeline-config-container">
        <!-- 应用信息 -->
        <Card size="small" class="mb-4">
          <Descriptions :column="4" size="small">
            <DescriptionsItem label="应用名称">{{ app.name }}</DescriptionsItem>
            <DescriptionsItem label="应用编码">{{ app.code }}</DescriptionsItem>
            <DescriptionsItem label="应用类型">{{ app.app_type_display }}</DescriptionsItem>
            <DescriptionsItem label="构建分支">{{ app.build_branch || 'main' }}</DescriptionsItem>
          </Descriptions>
        </Card>

        <!-- 配置列表 -->
        <Tabs v-model:activeKey="activeTab" @change="onTabChange">
          <TabPane key="ci" tab="CI 配置">
            <!-- 创建配置按钮 -->
            <div class="mb-4">
              <Button type="primary" @click="showCreateForm = true" v-if="!showCreateForm">
                + 新建 CI 配置
              </Button>
            </div>

            <!-- 创建配置表单 -->
            <Card v-if="showCreateForm" size="small" class="mb-4" title="新建配置">
              <Form layout="vertical">
                <div class="grid grid-cols-2 gap-4">
                  <FormItem label="配置类型" required>
                    <Select v-model:value="createFormState.config_type" disabled>
                      <SelectOption v-for="opt in CONFIG_TYPE_OPTIONS" :key="opt.value" :value="opt.value">
                        {{ opt.label }}
                      </SelectOption>
                    </Select>
                  </FormItem>
                  <FormItem label="环境" required>
                    <Select v-model:value="createFormState.environment" placeholder="选择环境">
                      <SelectOption v-for="opt in ENVIRONMENT_OPTIONS" :key="opt.value" :value="opt.value">
                        {{ opt.label }}
                      </SelectOption>
                    </Select>
                  </FormItem>
                </div>

                <FormItem label="关联模板">
                  <Select
                    v-model:value="createFormState.template"
                    placeholder="选择模板"
                    allow-clear
                    show-search
                    :filter-option="filterOption"
                    @change="(val) => handleTemplateChange(val as number | undefined)"
                  >
                    <SelectOption
                      v-for="tpl in filteredTemplates"
                      :key="tpl.id"
                      :value="tpl.id"
                      :label="tpl.name"
                    >
                      {{ tpl.name }} ({{ tpl.language }}{{ tpl.framework ? '/' + tpl.framework : '' }})
                    </SelectOption>
                  </Select>
                </FormItem>

                <FormItem v-if="templateVersions.length > 0" label="模板版本">
                  <Select v-model:value="createFormState.template_version" placeholder="选择版本（默认最新）">
                    <SelectOption
                      v-for="ver in templateVersions"
                      :key="ver.id"
                      :value="ver.id"
                    >
                      v{{ ver.version }} {{ ver.is_latest ? '(最新)' : '' }}
                    </SelectOption>
                  </Select>
                </FormItem>

                <Divider>或者</Divider>

                <FormItem label="自定义 Jenkinsfile">
                  <Textarea
                    v-model:value="createFormState.custom_content"
                    placeholder="不使用模板时，可直接填写 Jenkinsfile 内容"
                    :rows="6"
                    class="font-mono"
                  />
                </FormItem>

                <FormItem>
                  <Space>
                    <Button type="primary" :loading="createLoading" @click="handleCreateConfig">
                      创建配置
                    </Button>
                    <Button @click="showCreateForm = false; resetCreateForm()">
                      取消
                    </Button>
                  </Space>
                </FormItem>
              </Form>
            </Card>

            <div v-if="ciConfigs.length === 0 && !showCreateForm" class="p-8">
              <Empty description="暂无 CI 配置，点击上方按钮创建" />
            </div>
            <div v-else-if="ciConfigs.length > 0" class="config-list">
              <Card
                v-for="config in ciConfigs"
                :key="config.id"
                size="small"
                class="mb-3"
                :title="`${getEnvironmentDisplay(config.environment)} - ${getConfigTypeDisplay(config.config_type)}`"
              >
                <template #extra>
                  <Space>
                    <Tag :color="getSyncTag(config).color">
                      {{ getSyncTag(config).text }}
                    </Tag>
                    <Tooltip v-if="config.jenkins_sync_time" :title="format_datetime(config.jenkins_sync_time)">
                      <span class="text-gray-500 text-xs">
                        {{ format_datetime(config.jenkins_sync_time) }}
                      </span>
                    </Tooltip>
                  </Space>
                </template>

                <Descriptions :column="2" size="small">
                  <DescriptionsItem label="关联模板">{{ config.template_name || '自定义' }}</DescriptionsItem>
                  <DescriptionsItem label="当前版本">v{{ config.current_version }}</DescriptionsItem>
                  <DescriptionsItem v-if="config.jenkins_job_name" label="Jenkins Job">
                    <Tooltip :title="config.jenkins_job_name">
                      <Tag color="blue">{{ config.jenkins_job_name }}</Tag>
                    </Tooltip>
                  </DescriptionsItem>
                  <DescriptionsItem v-if="config.jenkins_sync_message" label="同步消息">
                    <span :class="{ 'text-red-500': config.jenkins_sync_status === 3 }">
                      {{ config.jenkins_sync_message }}
                    </span>
                  </DescriptionsItem>
                </Descriptions>

                <div class="mt-3 flex gap-2">
                  <Button
                    type="primary"
                    size="small"
                    :loading="generating === config.id"
                    @click="handleGenerateAndSync(config)"
                  >
                    生成并同步
                  </Button>
                  <Button
                    size="small"
                    :loading="generating === config.id"
                    @click="handleGenerate(config)"
                  >
                    生成 Jenkinsfile
                  </Button>
                  <Button
                    size="small"
                    :loading="syncing === config.id"
                    :disabled="config.current_version === 0"
                    @click="handleSync(config)"
                  >
                    同步到 Jenkins
                  </Button>
                  <Button size="small" @click="handleViewVersions(config)">
                    版本历史
                  </Button>
                </div>
              </Card>
            </div>
          </TabPane>

          <TabPane key="cd" tab="CD 配置">
            <!-- 创建配置按钮 -->
            <div class="mb-4">
              <Button type="primary" @click="showCreateForm = true" v-if="!showCreateForm">
                + 新建 CD 配置
              </Button>
            </div>

            <!-- 创建配置表单 -->
            <Card v-if="showCreateForm" size="small" class="mb-4" title="新建配置">
              <Form layout="vertical">
                <div class="grid grid-cols-2 gap-4">
                  <FormItem label="配置类型" required>
                    <Select v-model:value="createFormState.config_type" disabled>
                      <SelectOption v-for="opt in CONFIG_TYPE_OPTIONS" :key="opt.value" :value="opt.value">
                        {{ opt.label }}
                      </SelectOption>
                    </Select>
                  </FormItem>
                  <FormItem label="环境" required>
                    <Select v-model:value="createFormState.environment" placeholder="选择环境">
                      <SelectOption v-for="opt in ENVIRONMENT_OPTIONS" :key="opt.value" :value="opt.value">
                        {{ opt.label }}
                      </SelectOption>
                    </Select>
                  </FormItem>
                </div>

                <FormItem label="关联模板">
                  <Select
                    v-model:value="createFormState.template"
                    placeholder="选择模板"
                    allow-clear
                    show-search
                    :filter-option="filterOption"
                    @change="(val) => handleTemplateChange(val as number | undefined)"
                  >
                    <SelectOption
                      v-for="tpl in filteredTemplates"
                      :key="tpl.id"
                      :value="tpl.id"
                      :label="tpl.name"
                    >
                      {{ tpl.name }} ({{ tpl.language }}{{ tpl.framework ? '/' + tpl.framework : '' }})
                    </SelectOption>
                  </Select>
                </FormItem>

                <FormItem v-if="templateVersions.length > 0" label="模板版本">
                  <Select v-model:value="createFormState.template_version" placeholder="选择版本（默认最新）">
                    <SelectOption
                      v-for="ver in templateVersions"
                      :key="ver.id"
                      :value="ver.id"
                    >
                      v{{ ver.version }} {{ ver.is_latest ? '(最新)' : '' }}
                    </SelectOption>
                  </Select>
                </FormItem>

                <Divider>或者</Divider>

                <FormItem label="自定义 Jenkinsfile">
                  <Textarea
                    v-model:value="createFormState.custom_content"
                    placeholder="不使用模板时，可直接填写 Jenkinsfile 内容"
                    :rows="6"
                    class="font-mono"
                  />
                </FormItem>

                <FormItem>
                  <Space>
                    <Button type="primary" :loading="createLoading" @click="handleCreateConfig">
                      创建配置
                    </Button>
                    <Button @click="showCreateForm = false; resetCreateForm()">
                      取消
                    </Button>
                  </Space>
                </FormItem>
              </Form>
            </Card>

            <div v-if="cdConfigs.length === 0 && !showCreateForm" class="p-8">
              <Empty description="暂无 CD 配置，点击上方按钮创建" />
            </div>
            <div v-else-if="cdConfigs.length > 0" class="config-list">
              <Card
                v-for="config in cdConfigs"
                :key="config.id"
                size="small"
                class="mb-3"
                :title="`${getEnvironmentDisplay(config.environment)} - ${getConfigTypeDisplay(config.config_type)}`"
              >
                <template #extra>
                  <Space>
                    <Tag :color="getSyncTag(config).color">
                      {{ getSyncTag(config).text }}
                    </Tag>
                    <Tooltip v-if="config.jenkins_sync_time" :title="format_datetime(config.jenkins_sync_time)">
                      <span class="text-gray-500 text-xs">
                        {{ format_datetime(config.jenkins_sync_time) }}
                      </span>
                    </Tooltip>
                  </Space>
                </template>

                <Descriptions :column="2" size="small">
                  <DescriptionsItem label="关联模板">{{ config.template_name || '自定义' }}</DescriptionsItem>
                  <DescriptionsItem label="当前版本">v{{ config.current_version }}</DescriptionsItem>
                  <DescriptionsItem v-if="config.jenkins_job_name" label="Jenkins Job">
                    <Tooltip :title="config.jenkins_job_name">
                      <Tag color="blue">{{ config.jenkins_job_name }}</Tag>
                    </Tooltip>
                  </DescriptionsItem>
                  <DescriptionsItem v-if="config.jenkins_sync_message" label="同步消息">
                    <span :class="{ 'text-red-500': config.jenkins_sync_status === 3 }">
                      {{ config.jenkins_sync_message }}
                    </span>
                  </DescriptionsItem>
                </Descriptions>

                <div class="mt-3 flex gap-2">
                  <Button
                    type="primary"
                    size="small"
                    :loading="generating === config.id"
                    @click="handleGenerateAndSync(config)"
                  >
                    生成并同步
                  </Button>
                  <Button
                    size="small"
                    :loading="generating === config.id"
                    @click="handleGenerate(config)"
                  >
                    生成 Jenkinsfile
                  </Button>
                  <Button
                    size="small"
                    :loading="syncing === config.id"
                    :disabled="config.current_version === 0"
                    @click="handleSync(config)"
                  >
                    同步到 Jenkins
                  </Button>
                  <Button size="small" @click="handleViewVersions(config)">
                    版本历史
                  </Button>
                </div>
              </Card>
            </div>
          </TabPane>
        </Tabs>

        <!-- 版本历史弹窗 -->
        <Card v-if="showVersionHistory && activeConfig" size="small" class="mt-4" title="版本历史">
          <template #extra>
            <Button size="small" @click="showVersionHistory = false">关闭</Button>
          </template>
          <Table
            :columns="versionColumns"
            :data-source="versions"
            :pagination="false"
            size="small"
            row-key="id"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'action'">
                <Button type="link" size="small" @click="jenkinsfileContent = record.content">
                  查看
                </Button>
              </template>
              <template v-else-if="column.dataIndex === 'create_time'">
                {{ format_datetime(record.create_time) }}
              </template>
            </template>
          </Table>
        </Card>

        <!-- Jenkinsfile 预览 -->
        <Card v-if="jenkinsfileContent" size="small" class="mt-4" title="Jenkinsfile 预览">
          <template #extra>
            <Button size="small" @click="jenkinsfileContent = ''">关闭</Button>
          </template>
          <Textarea
            :value="jenkinsfileContent"
            :auto-size="{ minRows: 10, maxRows: 20 }"
            readonly
            class="font-mono text-sm"
          />
        </Card>
      </div>
    </Spin>
  </Modal>
</template>

<style scoped>
.pipeline-config-container {
  max-height: 70vh;
  overflow-y: auto;
}

.config-list {
  max-height: 400px;
  overflow-y: auto;
}
</style>
