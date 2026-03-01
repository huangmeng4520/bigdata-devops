<script lang="ts" setup>
import type { PipelineTemplateApi } from '#/api/release';

import { ref, computed } from 'vue';

import { useVbenModal } from '@vben/common-ui';

import { message, Modal as AModal } from 'ant-design-vue';

import {
  autoVersionIncrement,
  createTemplateVersion,
  getTemplateVersions,
  getVersionDetail,
  setLatestVersion,
  updateVersion,
  updateVersionContent,
} from '#/api/release';
import {
  parseStages,
  extractStageScript,
  updateStageSteps,
  validateJenkinsfile,
} from '../utils/jenkinsfileParser';

const emit = defineEmits(['success']);

const [Modal, modalApi] = useVbenModal({
  async onConfirm() {
    modalApi.close();
  },
  async onOpenChange(isOpen) {
    if (isOpen) {
      const data = modalApi.getData<PipelineTemplateApi.Template>();
      if (!data) {
        message.error('未获取到模板数据');
        modalApi.close();
        return;
      }
      currentTemplate.value = data;
      showNewVersionForm.value = false;
      await loadVersions();
    }
  },
});

const currentTemplate = ref<PipelineTemplateApi.Template | null>(null);
const versionList = ref<PipelineTemplateApi.TemplateVersion[]>([]);
const loading = ref(false);

// 显示新建版本表单
const showNewVersionForm = ref(false);
const newVersionData = ref({
  version: '',
  content: '',
  change_log: '',
  is_latest: false,
});

// 查看版本内容
const showContentModal = ref(false);
const currentVersionContent = ref('');
const currentViewVersion = ref('');

// 版本列表列配置
const versionColumns = [
  {
    title: '版本号',
    dataIndex: 'version',
    width: 100,
  },
  {
    title: '状态',
    dataIndex: 'status',
    width: 80,
  },
  {
    title: '变更日志',
    dataIndex: 'change_log',
    ellipsis: true,
  },
  {
    title: '创建时间',
    dataIndex: 'create_time',
    width: 160,
  },
  {
    title: '操作',
    key: 'action',
    width: 400,
    fixed: 'right',
  },
];

const modalTitle = computed(() => {
  return currentTemplate.value ? `${currentTemplate.value.name} - 版本管理` : '版本管理';
});

// 加载版本列表
async function loadVersions() {
  if (!currentTemplate.value?.id) return;
  loading.value = true;
  try {
    const result = await getTemplateVersions(currentTemplate.value.id);
    console.log('版本列表响应:', result);
    // 响应拦截器已提取 data 字段，result 格式为 { items: [...], total: number }
    versionList.value = result?.items || [];
    console.log('版本列表数据:', versionList.value);
  } catch (error: any) {
    message.error(error?.message || '加载版本列表失败');
  } finally {
    loading.value = false;
  }
}

// 自动生成版本号
function generateNextVersion(): string {
  if (versionList.value.length === 0) return '1.0.0';

  // 找到最新版本
  const latest = versionList.value.find(v => v.is_latest) || versionList.value[0];
  const versionParts = latest.version.split('.');

  if (versionParts.length >= 3) {
    // 递增最后一个数字
    const lastNum = parseInt(versionParts[2]) || 0;
    versionParts[2] = String(lastNum + 1);
    return versionParts.join('.');
  } else if (versionParts.length === 2) {
    const lastNum = parseInt(versionParts[1]) || 0;
    versionParts[1] = String(lastNum + 1);
    return versionParts.join('.');
  }
  return '1.0.0';
}

// 验证 Jenkinsfile 格式
function validateJenkinsfileContent() {
  const result = validateJenkinsfile(newVersionData.value.content);
  if (result.valid) {
    message.success('Jenkinsfile 格式验证通过');
  } else {
    message.error('Jenkinsfile 格式错误：' + result.error);
  }
}

// 显示创建表单时自动生成版本号
function onShowCreateForm() {
  showNewVersionForm.value = true;
  newVersionData.value = {
    version: generateNextVersion(),
    content: '',
    change_log: '',
    is_latest: false,
  };
}

// 创建新版本
async function handleCreateVersion() {
  if (!currentTemplate.value?.id) return;
  if (!newVersionData.value.version) {
    message.error('请输入版本号');
    return;
  }
  try {
    await createTemplateVersion(currentTemplate.value.id, newVersionData.value);
    message.success('版本创建成功');
    showNewVersionForm.value = false;
    await loadVersions();
    emit('success');
  } catch (error: any) {
    message.error(error?.message || '创建失败');
  }
}

// 设为最新版本
async function handleSetLatest(version: PipelineTemplateApi.TemplateVersion) {
  try {
    await setLatestVersion(version.id);
    message.success('已设为最新版本');
    await loadVersions();
    emit('success');
  } catch {
    message.error('操作失败');
  }
}

// 查看版本内容
async function handleViewContent(version: PipelineTemplateApi.TemplateVersion) {
  try {
    const detail = await getVersionDetail(version.id);
    currentVersionContent.value = detail.content || version.content || '';
    currentViewVersion.value = version.version;
    showContentModal.value = true;
  } catch {
    // 如果获取详情失败，使用列表中的内容
    currentVersionContent.value = version.content || '(无内容)';
    currentViewVersion.value = version.version;
    showContentModal.value = true;
  }
}

// 编辑版本内容
const showEditContentModal = ref(false);
const editingVersion = ref<PipelineTemplateApi.TemplateVersion | null>(null);
const editingContent = ref('');

async function handleEditContent(version: PipelineTemplateApi.TemplateVersion) {
  try {
    const detail = await getVersionDetail(version.id);
    editingVersion.value = detail;
    editingContent.value = detail.content || '';
    showEditContentModal.value = true;
  } catch {
    message.error('加载版本详情失败');
  }
}

async function handleSaveContent() {
  if (!editingVersion.value) return;

  try {
    await updateVersionContent(editingVersion.value.id, editingContent.value);
    message.success('内容更新成功');
    showEditContentModal.value = false;
    await loadVersions();
    emit('success');
  } catch (error: any) {
    message.error(error?.message || '更新失败');
  }
}

// 编辑版本（版本号 + 内容）
const showEditVersionModal = ref(false);
const editingVersionData = ref<PipelineTemplateApi.TemplateVersion | null>(null);
const editVersionForm = ref({
  version: '',
  content: '',
  change_log: '',
});

async function handleEditVersion(version: PipelineTemplateApi.TemplateVersion) {
  try {
    const detail = await getVersionDetail(version.id);
    editingVersionData.value = detail;
    editVersionForm.value = {
      version: detail.version || '',
      content: detail.content || '',
      change_log: detail.change_log || '',
    };
    showEditVersionModal.value = true;
  } catch {
    message.error('加载版本详情失败');
  }
}

async function handleSaveVersion() {
  if (!editingVersionData.value) return;
  if (!editVersionForm.value.version) {
    message.error('请输入版本号');
    return;
  }

  try {
    await updateVersion(editingVersionData.value.id, {
      version: editVersionForm.value.version,
      content: editVersionForm.value.content,
      change_log: editVersionForm.value.change_log,
    });
    message.success('版本更新成功');
    showEditVersionModal.value = false;
    await loadVersions();
    emit('success');
  } catch (error: any) {
    message.error(error?.message || '更新失败');
  }
}

// 从最新版本复制内容
async function copyFromLatest() {
  const latest = versionList.value.find((v) => v.is_latest);
  if (latest) {
    try {
      const detail = await getVersionDetail(latest.id);
      newVersionData.value.content = detail.content || '';
      message.success('已复制最新版本内容');
    } catch {
      newVersionData.value.content = latest.content || '';
      message.success('已复制最新版本内容');
    }
  } else {
    message.warning('没有最新版本可复制');
  }
}

// 自动版本迭代
async function handleAutoVersion(version: PipelineTemplateApi.TemplateVersion) {
  AModal.confirm({
    title: '自动版本迭代',
    content: '将基于当前版本自动创建新版本（版本号自动递增），是否继续？',
    onOk: async () => {
      try {
        await autoVersionIncrement(version.id, '自动版本迭代');
        message.success('新版本创建成功');
        await loadVersions();
        emit('success');
      } catch (error: any) {
        message.error(error?.message || '操作失败');
      }
    },
  });
}

// 编辑阶段
const showStageEditor = ref(false);
const currentEditVersion = ref<PipelineTemplateApi.TemplateVersion | null>(null);
const currentEditTemplateId = ref<number | null>(null);
const availableStages = ref<{ name: string; content: string }[]>([]);
const currentStageName = ref('');
const currentStageScript = ref('');
const originalJenkinsfile = ref('');

async function handleEditStage(version: PipelineTemplateApi.TemplateVersion) {
  try {
    const detail = await getVersionDetail(version.id);
    currentEditVersion.value = detail;
    // 保存模板ID（可能是对象或ID）
    currentEditTemplateId.value = typeof detail.template === 'object' ? detail.template?.id : detail.template;
    originalJenkinsfile.value = detail.content || '';

    // 解析 Jenkinsfile 中的 stages
    const stages = parseStages(originalJenkinsfile.value);
    availableStages.value = stages.map((stage) => ({
      name: stage.name,
      content: extractStageScript(stage.content),
    }));

    // 默认选择第一个 stage
    if (availableStages.value.length > 0) {
      currentStageName.value = availableStages.value[0].name;
      currentStageScript.value = availableStages.value[0].content;
    } else {
      currentStageName.value = '';
      currentStageScript.value = '';
      message.warning('未在 Jenkinsfile 中检测到 stages');
    }

    showStageEditor.value = true;
  } catch (error: any) {
    message.error('加载版本详情失败：' + (error?.message || '未知错误'));
  }
}

function onStageChange(stageName: string) {
  const stage = availableStages.value.find((s) => s.name === stageName);
  if (stage) {
    currentStageScript.value = stage.content;
  }
}

async function handleSaveStage() {
  if (!currentEditVersion.value || !currentStageName.value) {
    message.error('请选择阶段');
    return;
  }

  try {
    // 更新 Jenkinsfile 中对应 stage 的内容
    const updatedJenkinsfile = updateStageSteps(
      originalJenkinsfile.value,
      currentStageName.value,
      currentStageScript.value
    );

    // 验证更新后的 Jenkinsfile
    const validation = validateJenkinsfile(updatedJenkinsfile);
    if (!validation.valid) {
      message.error('Jenkinsfile 格式错误：' + validation.error);
      return;
    }

    // 自动生成新版本号
    const nextVersion = generateNextVersion();

    // 创建新版本（自动递增版本号）
    if (!currentEditTemplateId.value) {
      message.error('无法获取模板ID');
      return;
    }
    await createTemplateVersion(currentEditTemplateId.value, {
      version: nextVersion,
      content: updatedJenkinsfile,
      change_log: `编辑 Stage: ${currentStageName.value}`,
      is_latest: true,
    });

    message.success(`已自动创建新版本 ${nextVersion}`);
    showStageEditor.value = false;
    await loadVersions();
    emit('success');
  } catch (error: any) {
    message.error(error?.message || '更新失败');
  }
}


</script>

<template>
  <Modal :title="modalTitle" class="w-[900px]" :body-style="{ minHeight: '500px' }">
    <div class="mb-4">
      <a-button type="primary" @click="onShowCreateForm">
        创建新版本
      </a-button>
    </div>

    <!-- 新建版本表单 -->
    <a-card v-if="showNewVersionForm" title="创建新版本" class="mb-4" :bordered="false">
      <template #extra>
        <a-space>
          <a-button size="small" @click="copyFromLatest">从最新版本复制</a-button>
          <a-button size="small" @click="validateJenkinsfileContent">验证格式</a-button>
          <a-button size="small" @click="showNewVersionForm = false">取消</a-button>
          <a-button type="primary" size="small" @click="handleCreateVersion">创建版本</a-button>
        </a-space>
      </template>
      
      <a-row :gutter="16" class="mb-4">
        <a-col :span="8">
          <a-form-item label="版本号" required>
            <a-input v-model:value="newVersionData.version" placeholder="如: 1.0.0" />
          </a-form-item>
        </a-col>
        <a-col :span="8">
          <a-form-item label="设为最新版本">
            <a-switch v-model:checked="newVersionData.is_latest" checked-children="是" un-checked-children="否" />
          </a-form-item>
        </a-col>
        <a-col :span="8">
          <a-form-item label="变更日志">
            <a-input v-model:value="newVersionData.change_log" placeholder="描述本次版本变更内容..." />
          </a-form-item>
        </a-col>
      </a-row>

      <!-- Jenkinsfile 编辑器 -->
      <div class="jenkinsfile-editor">
        <div class="editor-header">
          <span class="editor-title">Jenkinsfile</span>
          <span class="editor-language">Groovy</span>
        </div>
        <a-textarea
          v-model:value="newVersionData.content"
          placeholder="// 输入 Jenkinsfile 内容
pipeline {
    agent any
    stages {
        stage('Example') {
            steps {
                echo 'Hello World'
            }
        }
    }
}"
          :rows="20"
          class="editor-textarea"
        />
        <div class="editor-footer">
          <span class="text-gray-500 text-xs">
            支持标准 Jenkins Pipeline 语法
          </span>
        </div>
      </div>
    </a-card>

    <!-- 版本列表 -->
    <div class="mb-2 text-gray-600">
      共 {{ versionList.length }} 个版本
    </div>
    <a-table
      :columns="versionColumns"
      :data-source="versionList"
      :loading="loading"
      :locale="{ emptyText: '暂无版本数据' }"
      :pagination="false"
      :scroll="{ x: 900 }"
      row-key="id"
      size="small"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.dataIndex === 'version'">
          <span class="font-mono">{{ record.version }}</span>
          <a-tag v-if="record.is_latest" color="green" class="ml-2">最新</a-tag>
        </template>
        <template v-else-if="column.dataIndex === 'status'">
          <a-tag :color="record.status === 1 ? 'success' : 'error'">
            {{ record.status === 1 ? '启用' : '禁用' }}
          </a-tag>
        </template>
        <template v-else-if="column.key === 'action'">
          <a-space wrap size="small">
            <a-button v-if="!record.is_latest" type="link" size="small" @click="handleSetLatest(record)">设为最新</a-button>
            <a-button type="link" size="small" @click="handleEditVersion(record)">编辑版本</a-button>
            <a-button type="link" size="small" @click="handleEditStage(record)">编辑Stage</a-button>
            <a-button type="link" size="small" @click="handleAutoVersion(record)">自动迭代</a-button>
            <a-button type="link" size="small" @click="handleViewContent(record)">查看</a-button>
          </a-space>
        </template>
      </template>
    </a-table>

    <!-- 版本内容预览模态框 -->
    <AModal
      v-model:open="showContentModal"
      :title="`版本 ${currentViewVersion} 内容`"
      :width="800"
      :footer="null"
    >
      <pre class="bg-gray-50 p-4 rounded overflow-auto max-h-[500px] text-sm font-mono whitespace-pre-wrap">{{ currentVersionContent }}</pre>
    </AModal>

    <!-- 编辑内容模态框 -->
    <AModal
      v-model:open="showEditContentModal"
      :title="`编辑版本 ${editingVersion?.version} 内容`"
      :width="900"
      @ok="handleSaveContent"
    >
      <a-textarea
        v-model:value="editingContent"
        :rows="20"
        class="font-mono text-sm"
        placeholder="输入 Jenkinsfile 内容"
      />
    </AModal>

    <!-- 编辑版本模态框（版本号 + Jenkinsfile） -->
    <AModal
      v-model:open="showEditVersionModal"
      :title="`编辑版本 ${editingVersionData?.version}`"
      :width="900"
      @ok="handleSaveVersion"
    >
      <a-row :gutter="16" class="mb-4">
        <a-col :span="12">
          <a-form-item label="版本号" required>
            <a-input
              v-model:value="editVersionForm.version"
              placeholder="如: 1.0.0"
            />
          </a-form-item>
        </a-col>
        <a-col :span="12">
          <a-form-item label="变更日志">
            <a-input
              v-model:value="editVersionForm.change_log"
              placeholder="版本变更说明"
            />
          </a-form-item>
        </a-col>
      </a-row>
      
      <!-- Jenkinsfile 编辑器 -->
      <div class="jenkinsfile-editor">
        <div class="editor-header">
          <span class="editor-title">Jenkinsfile</span>
          <span class="editor-language">Groovy</span>
        </div>
        <a-textarea
          v-model:value="editVersionForm.content"
          :rows="18"
          class="editor-textarea"
          placeholder="输入 Jenkinsfile 内容"
        />
        <div class="editor-footer">
          <span class="text-gray-500 text-xs">
            支持标准 Jenkins Pipeline 语法
          </span>
        </div>
      </div>
    </AModal>

    <!-- 阶段编辑模态框 -->
    <AModal
      v-model:open="showStageEditor"
      :title="`编辑 Stage - 基于版本 ${currentEditVersion?.version}`"
      :width="900"
      @ok="handleSaveStage"
    >
      <a-alert
        v-if="availableStages.length > 0"
        type="info"
        class="mb-4"
        message="保存后将自动创建新版本（版本号自动递增），不会修改原版本"
        banner
      />
      <div v-if="availableStages.length > 0">
        <a-form-item label="选择 Stage" required class="mb-4">
          <a-select
            v-model:value="currentStageName"
            style="width: 300px"
            placeholder="请选择要编辑的 Stage"
            @change="onStageChange"
          >
            <a-select-option
              v-for="stage in availableStages"
              :key="stage.name"
              :value="stage.name"
            >
              {{ stage.name }}
            </a-select-option>
          </a-select>
        </a-form-item>
        
        <!-- Stage 脚本编辑器 -->
        <div class="jenkinsfile-editor">
          <div class="editor-header">
            <span class="editor-title">{{ currentStageName }} - Steps 脚本</span>
            <span class="editor-language">Groovy</span>
          </div>
          <a-textarea
            v-model:value="currentStageScript"
            :rows="16"
            class="editor-textarea"
            placeholder="输入该 Stage 的脚本内容，例如：
sh 'echo Hello World'
sh 'mvn clean package'
echo 'Build completed'"
          />
          <div class="editor-footer">
            <span class="text-gray-500 text-xs">
              编辑的是 Stage 中 steps 部分的内容，保存后自动更新 Jenkinsfile 并创建新版本
            </span>
          </div>
        </div>
      </div>
      <div v-else class="text-center py-8 text-gray-500">
        未在 Jenkinsfile 中检测到可编辑的 Stage<br>
        请确保 Jenkinsfile 格式正确，包含 stages 定义
      </div>
    </AModal>
  </Modal>
</template>

<style scoped>
.jenkinsfile-editor {
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  overflow: hidden;
  background-color: #fff;
}

.jenkinsfile-editor .editor-textarea {
  display: block;
  width: 100%;
  min-height: 400px;
  padding: 12px;
  border: none;
  outline: none;
}

.editor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background-color: #f5f5f5;
  border-bottom: 1px solid #d9d9d9;
}

.editor-title {
  font-weight: 500;
  color: #262626;
  display: flex;
  align-items: center;
}

.editor-language {
  font-size: 12px;
  color: #8c8c8c;
  background-color: #e6e6e6;
  padding: 2px 8px;
  border-radius: 4px;
}

.editor-textarea {
  font-family: 'Menlo', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  resize: vertical;
  width: 100%;
}

.editor-textarea:focus {
  border-color: #40a9ff;
  box-shadow: 0 0 0 2px rgba(24, 144, 255, 0.2);
}

.editor-footer {
  padding: 8px 12px;
  background-color: #fafafa;
  border-top: 1px solid #d9d9d9;
}

:deep(.ant-card) {
  background-color: #fafafa;
}

:deep(.ant-card-head) {
  background-color: #f0f0f0;
  font-weight: 500;
}

:deep(.ant-form-item) {
  margin-bottom: 16px;
}
</style>
