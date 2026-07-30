<script lang="ts" setup>
import type { PipelineTemplateApi } from '#/api/release';

import { ref, computed } from 'vue';

import { useVbenModal } from '@vben/common-ui';

import { message, Modal as AModal, Drawer, Select, SelectOption, Alert } from 'ant-design-vue';

import {
  createTemplateVersion,
  deleteTemplateVersion,
  getTemplateVersions,
  getVersionDetail,
  setLatestVersion,
} from '#/api/release';
import {
  parseStages,
  extractStageScript,
  updateStageSteps,
  extractEnvironment,
  updateEnvironment,
  validateJenkinsfile,
} from '../utils/jenkinsfileParser';

const emit = defineEmits(['success']);

// 关闭版本管理弹窗
function handleClose() {
  detailDrawerVisible.value = false;
  modalApi.close();
}

const [Modal, modalApi] = useVbenModal({
  onConfirm: handleClose,
  async onOpenChange(isOpen) {
    if (isOpen) {
      const data = modalApi.getData<PipelineTemplateApi.Template>();
      if (!data) {
        message.error('未获取到模板数据');
        modalApi.close();
        return;
      }
      currentTemplate.value = data;
      viewMode.value = 'list';
      await loadVersions();
    }
  },
});

const currentTemplate = ref<PipelineTemplateApi.Template | null>(null);
const versionList = ref<PipelineTemplateApi.TemplateVersion[]>([]);
const loading = ref(false);
const viewMode = ref<'list' | 'create'>('list');

// 详情抽屉
const detailDrawerVisible = ref(false);
const currentDetailVersion = ref<PipelineTemplateApi.TemplateVersion | null>(null);
const detailLoading = ref(false);
const deletingId = ref<number | null>(null);

// 创建新版本
const newVersionData = ref({
  version: '',
  content: '',
  change_log: '',
  is_latest: true,
});

const stageSaving = ref(false);
const envSaving = ref(false);

// Stage 编辑
const stageEditorVisible = ref(false);
const availableStages = ref<{ name: string; content: string }[]>([]);
const currentStageName = ref('');
const currentStageScript = ref('');
const originalJenkinsfile = ref('');

// Environment 编辑
const envEditorVisible = ref(false);
const currentEnvContent = ref('');

// 版本对比
const compareVisible = ref(false);
const compareVersions = ref<{ from: string; to: string }>({ from: '', to: '' });
const compareFromVersion = ref<PipelineTemplateApi.TemplateVersion | null>(null);
const compareToVersion = ref<PipelineTemplateApi.TemplateVersion | null>(null);

const modalTitle = computed(() => {
  return currentTemplate.value ? `${currentTemplate.value.name}` : '版本管理';
});

// 加载版本列表
async function loadVersions() {
  if (!currentTemplate.value?.id) return;
  loading.value = true;
  try {
    const result = await getTemplateVersions(currentTemplate.value.id);
    versionList.value = result?.items || [];
  } catch (error: any) {
    message.error(error?.message || '加载版本列表失败');
  } finally {
    loading.value = false;
  }
}

// 自动生成版本号
function generateNextVersion(): string {
  if (versionList.value.length === 0) return '1.0.0';
  const latest = versionList.value.find(v => v.is_latest) || versionList.value[0];
  const versionParts = latest.version.split('.');
  if (versionParts.length >= 3) {
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

// 显示创建表单（默认带最新版本内容，减少空白起步）
function showCreateForm() {
  const latest = versionList.value.find(v => v.is_latest) || versionList.value[0];
  newVersionData.value = {
    version: generateNextVersion(),
    content: latest?.content || '',
    change_log: '',
    is_latest: true,
  };
  viewMode.value = 'create';
}

// 从最新版本复制
async function copyFromLatest() {
  const latest = versionList.value.find(v => v.is_latest);
  if (!latest) {
    message.warning('没有最新版本可复制');
    return;
  }
  try {
    modalApi.lock();
    const detail = await getVersionDetail(latest.id);
    newVersionData.value.content = detail.content || '';
    message.success('已复制最新版本内容');
  } catch {
    newVersionData.value.content = latest.content || '';
    message.success('已复制最新版本内容');
  } finally {
    modalApi.lock(false);
  }
}

// 创建版本
async function handleCreateVersion() {
  if (!currentTemplate.value?.id) return;
  if (!newVersionData.value.version) {
    message.error('请输入版本号');
    return;
  }
  if (!newVersionData.value.content) {
    message.error('请输入 Jenkinsfile 内容');
    return;
  }

  // 验证格式
  const validation = validateJenkinsfile(newVersionData.value.content);
  if (!validation.valid) {
    message.error('Jenkinsfile 格式错误：' + validation.error);
    return;
  }

  try {
    modalApi.lock();
    await createTemplateVersion(currentTemplate.value.id, newVersionData.value);
    message.success('版本创建成功');
    viewMode.value = 'list';
    await loadVersions();
    emit('success');
  } catch (error: any) {
    message.error(error?.message || '创建失败');
  } finally {
    modalApi.lock(false);
  }
}

// 查看版本详情
async function viewVersionDetail(version: PipelineTemplateApi.TemplateVersion) {
  detailLoading.value = true;
  detailDrawerVisible.value = true;
  try {
    const detail = await getVersionDetail(version.id);
    currentDetailVersion.value = detail;
  } catch {
    currentDetailVersion.value = version;
  } finally {
    detailLoading.value = false;
  }
}

// 设为最新版本
async function handleSetLatest(version: PipelineTemplateApi.TemplateVersion) {
  try {
    modalApi.lock();
    await setLatestVersion(version.id);
    message.success('已设为最新版本');
    await loadVersions();
    emit('success');
  } catch {
    message.error('操作失败');
  } finally {
    modalApi.lock(false);
  }
}

// 删除版本（最新版本不可删除；已关联应用的版本禁止删除）
async function handleDeleteVersion(version: PipelineTemplateApi.TemplateVersion) {
  if (version.is_latest) {
    message.warning('最新版本不可删除');
    return;
  }
  AModal.confirm({
    title: '确认删除版本',
    content: `确定要删除版本「${version.version}」吗？删除后不可恢复。`,
    okText: '删除',
    okType: 'danger',
    cancelText: '取消',
    onOk: async () => {
      try {
        deletingId.value = version.id;
        await deleteTemplateVersion(version.id);
        message.success('删除成功');
        await loadVersions();
        emit('success');
      } catch (error: any) {
        message.error(error?.message || '删除失败');
      } finally {
        deletingId.value = null;
      }
    },
  });
}

// 编辑 Stage
async function handleEditStage(version: PipelineTemplateApi.TemplateVersion) {
  try {
    const detail = await getVersionDetail(version.id);
    originalJenkinsfile.value = detail?.content || '';
    const stages = parseStages(originalJenkinsfile.value);
    availableStages.value = stages.map(stage => ({
      name: stage.name,
      content: extractStageScript(stage.content),
    }));

    if (availableStages.value.length > 0) {
      currentStageName.value = availableStages.value[0].name;
      currentStageScript.value = availableStages.value[0].content;
    } else {
      currentStageName.value = '';
      currentStageScript.value = '';
      message.warning('未检测到可编辑的 Stage');
      return;
    }

    stageEditorVisible.value = true;
  } catch {
    message.error('加载版本详情失败');
  }
}

// Stage 切换
function onStageChange(stageName: string) {
  const stage = availableStages.value.find(s => s.name === stageName);
  if (stage) {
    currentStageScript.value = stage.content;
  }
}

// 保存 Stage 编辑
async function handleSaveStage() {
  if (!currentStageName.value || !currentTemplate.value?.id) return;

  try {
    stageSaving.value = true;
    const updatedJenkinsfile = updateStageSteps(
      originalJenkinsfile.value,
      currentStageName.value,
      currentStageScript.value
    );

    const validation = validateJenkinsfile(updatedJenkinsfile);
    if (!validation.valid) {
      message.error('Jenkinsfile 格式错误：' + validation.error);
      return;
    }

    const nextVersion = generateNextVersion();
    await createTemplateVersion(currentTemplate.value.id, {
      version: nextVersion,
      content: updatedJenkinsfile,
      change_log: `编辑 Stage: ${currentStageName.value}`,
      is_latest: true,
    });

    message.success(`已创建新版本 ${nextVersion}`);
    stageEditorVisible.value = false;
    await loadVersions();
    emit('success');
  } catch (error: any) {
    message.error(error?.message || '保存失败');
  } finally {
    stageSaving.value = false;
  }
}

// 编辑 Environment
async function handleEditEnvironment(version: PipelineTemplateApi.TemplateVersion) {
  try {
    const detail = await getVersionDetail(version.id);
    const content = detail?.content || '';

    const envContent = extractEnvironment(content);
    if (!envContent) {
      message.warning('未检测到 environment 块');
      return;
    }

    originalJenkinsfile.value = content;
    currentEnvContent.value = envContent;
    envEditorVisible.value = true;
  } catch (error: any) {
    message.error('加载版本详情失败');
  }
}

// 保存 Environment 编辑
async function handleSaveEnvironment() {
  if (!originalJenkinsfile.value || !currentTemplate.value?.id) return;

  try {
    envSaving.value = true;
    const updatedJenkinsfile = updateEnvironment(
      originalJenkinsfile.value,
      currentEnvContent.value
    );

    const validation = validateJenkinsfile(updatedJenkinsfile);
    if (!validation.valid) {
      message.error('Jenkinsfile 格式错误：' + validation.error);
      return;
    }

    const nextVersion = generateNextVersion();

    await createTemplateVersion(currentTemplate.value.id, {
      version: nextVersion,
      content: updatedJenkinsfile,
      change_log: '编辑 Environment',
      is_latest: true,
    });

    message.success(`已创建新版本 ${nextVersion}`);
    envEditorVisible.value = false;
    await loadVersions();
    emit('success');
  } catch (error: any) {
    message.error(error?.message || '保存失败');
  } finally {
    envSaving.value = false;
  }
}

// 版本对比
async function openCompare() {
  if (versionList.value.length < 2) {
    message.warning('至少需要 2 个版本才能对比');
    return;
  }

  // 找到最新版本和上个版本（按创建时间排序）
  const sortedVersions = [...versionList.value].sort((a, b) =>
    new Date(b.create_time).getTime() - new Date(a.create_time).getTime()
  );

  const latestVersion = sortedVersions[0];
  const prevVersion = sortedVersions[1];

  compareVersions.value = {
    from: prevVersion?.id?.toString() || '',
    to: latestVersion?.id?.toString() || '',
  };
  compareFromVersion.value = null;
  compareToVersion.value = null;
  compareVisible.value = true;

  // 自动加载对比内容
  await loadCompareVersions();
}

// 与上一个版本对比（基于当前选中的目标版本）
function compareWithPrev() {
  const toId = parseInt(compareVersions.value.to);
  if (!toId) {
    message.warning('请先选择目标版本');
    return;
  }
  const idx = versionList.value.findIndex(v => v.id === toId);
  const prev = versionList.value[idx + 1];
  if (!prev) {
    message.warning('该版本没有更早的版本可对比');
    return;
  }
  compareVersions.value = { from: String(prev.id), to: String(toId) };
  loadCompareVersions();
}

async function loadCompareVersions() {
  const fromId = parseInt(compareVersions.value.from);
  const toId = parseInt(compareVersions.value.to);

  if (!fromId || !toId) return;

  try {
    const [fromDetail, toDetail] = await Promise.all([
      getVersionDetail(fromId),
      getVersionDetail(toId),
    ]);
    compareFromVersion.value = fromDetail;
    compareToVersion.value = toDetail;
  } catch {
    message.error('加载版本详情失败');
  }
}

// 计算差异行
function computeDiffLines(oldContent: string, newContent: string) {
  const oldLines = (oldContent || '').split('\n');
  const newLines = (newContent || '').split('\n');

  const result: Array<{
    type: 'unchanged' | 'added' | 'removed';
    oldLine?: number;
    newLine?: number;
    content: string;
  }> = [];

  // 简单的行对行比较算法
  const maxLines = Math.max(oldLines.length, newLines.length);

  let oldIdx = 0;
  let newIdx = 0;

  while (oldIdx < oldLines.length || newIdx < newLines.length) {
    const oldLine = oldLines[oldIdx];
    const newLine = newLines[newIdx];

    if (oldIdx >= oldLines.length) {
      // 只剩新行
      result.push({ type: 'added', newLine: newIdx + 1, content: newLine });
      newIdx++;
    } else if (newIdx >= newLines.length) {
      // 只剩旧行
      result.push({ type: 'removed', oldLine: oldIdx + 1, content: oldLine });
      oldIdx++;
    } else if (oldLine === newLine) {
      // 相同行
      result.push({ type: 'unchanged', oldLine: oldIdx + 1, newLine: newIdx + 1, content: oldLine });
      oldIdx++;
      newIdx++;
    } else {
      // 检查是否是插入或删除
      const oldLineInNew = newLines.slice(newIdx).indexOf(oldLine);
      const newLineInOld = oldLines.slice(oldIdx).indexOf(newLine);

      if (oldLineInNew === -1 && newLineInOld === -1) {
        // 两边都是新内容，标记为修改
        result.push({ type: 'removed', oldLine: oldIdx + 1, content: oldLine });
        result.push({ type: 'added', newLine: newIdx + 1, content: newLine });
        oldIdx++;
        newIdx++;
      } else if (oldLineInNew !== -1 && (newLineInOld === -1 || oldLineInNew <= newLineInOld)) {
        // 新内容中插入了行
        result.push({ type: 'added', newLine: newIdx + 1, content: newLine });
        newIdx++;
      } else {
        // 旧内容中删除了行
        result.push({ type: 'removed', oldLine: oldIdx + 1, content: oldLine });
        oldIdx++;
      }
    }
  }

  return result;
}

// 格式化时间
function formatTime(time: string): string {
  if (!time) return '-';
  return new Date(time).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

// 获取状态标签颜色
function getStatusColor(version: PipelineTemplateApi.TemplateVersion): string {
  if (version.is_latest) return '#52c41a';
  return '#d9d9d9';
}
</script>

<template>
  <Modal :title="modalTitle" width="1000px" :footer="true" confirm-text="关闭">
    <!-- 头部操作栏 -->
    <div class="version-header">
      <div class="header-left">
        <span class="template-info">
          <span class="template-name">{{ currentTemplate?.name }}</span>
          <span class="template-code">{{ currentTemplate?.code }}</span>
        </span>
        <span class="version-count">共 {{ versionList.length }} 个版本</span>
      </div>
      <div class="header-right">
        <a-button v-if="versionList.length >= 2" @click="openCompare">
          版本对比
        </a-button>
        <a-button type="primary" @click="showCreateForm">
          新建版本
        </a-button>
      </div>
    </div>

    <!-- 创建版本视图 -->
    <div v-if="viewMode === 'create'" class="create-view">
      <div class="create-header">
        <a-button type="text" @click="viewMode = 'list'">
          ← 返回列表
        </a-button>
      </div>
      
      <div class="create-form">
        <div class="form-row">
          <div class="form-item">
            <label class="form-label required">版本号</label>
            <a-input v-model:value="newVersionData.version" placeholder="如: 1.0.0" style="width: 200px" />
          </div>
          <div class="form-item">
            <label class="form-label">变更说明</label>
            <a-input v-model:value="newVersionData.change_log" placeholder="描述本次版本变更内容" style="width: 300px" />
          </div>
          <div class="form-item">
            <a-switch v-model:checked="newVersionData.is_latest" checked-children="最新版本" un-checked-children="普通版本" />
          </div>
        </div>
        
        <div class="editor-container">
          <div class="editor-toolbar">
            <span class="editor-title">Jenkinsfile</span>
            <div class="editor-actions">
              <a-button size="small" @click="copyFromLatest">从最新版本复制</a-button>
              <a-button 
                size="small" 
                @click="() => {
                  const result = validateJenkinsfile(newVersionData.content);
                  if (result.valid) {
                    message.success('格式验证通过');
                  } else {
                    message.error('格式错误：' + result.error);
                  }
                }"
              >
                验证格式
              </a-button>
            </div>
          </div>
          <div class="editor-body">
            <textarea
              v-model="newVersionData.content"
              class="code-editor"
              placeholder="pipeline {
    agent any
    stages {
        stage('Build') {
            steps {
                echo 'Building...'
            }
        }
    }
}"
              spellcheck="false"
            />
          </div>
        </div>
        
        <div class="form-actions">
          <a-button @click="viewMode = 'list'">取消</a-button>
          <a-button type="primary" @click="handleCreateVersion">创建版本</a-button>
        </div>
      </div>
    </div>

    <!-- 版本列表视图 -->
    <div v-else class="version-list">
      <a-spin :spinning="loading">
        <div v-if="versionList.length === 0" class="empty-state">
          <div class="empty-icon">📦</div>
          <div class="empty-text">暂无版本</div>
          <a-button type="primary" @click="showCreateForm">创建第一个版本</a-button>
        </div>
        
        <div v-else class="version-timeline">
          <div
            v-for="(version, index) in versionList"
            :key="version.id"
            class="version-card"
            :class="{ 'is-latest': version.is_latest }"
          >
            <!-- 时间线指示器 -->
            <div class="timeline-indicator">
              <div class="timeline-dot" :style="{ backgroundColor: getStatusColor(version) }"></div>
              <div v-if="index < versionList.length - 1" class="timeline-line"></div>
            </div>
            
            <!-- 版本卡片内容 -->
            <div class="card-content">
              <div class="card-header">
                <div class="version-info">
                  <span class="version-number">{{ version.version }}</span>
                  <a-tag v-if="version.is_latest" color="success">最新版本</a-tag>
                  <a-tag :color="version.status === 1 ? 'blue' : 'default'">
                    {{ version.status === 1 ? '启用' : '禁用' }}
                  </a-tag>
                </div>
                <div class="version-time">{{ formatTime(version.create_time) }}</div>
              </div>
              
              <div class="card-body">
                <div class="change-log">
                  <span class="log-label">变更说明：</span>
                  <span class="log-content">{{ version.change_log || '无' }}</span>
                </div>
              </div>
              
              <div class="card-footer">
                <div class="footer-left">
                  <span class="creator">创建者：{{ version.creator || '系统' }}</span>
                </div>
                <div class="footer-actions">
                  <a-button size="small" @click="viewVersionDetail(version)">
                    查看详情
                  </a-button>
                  <a-button v-if="!version.is_latest" size="small" @click="handleSetLatest(version)">
                    设为最新
                  </a-button>
                  <a-button type="primary" size="small" ghost @click="handleEditStage(version)">
                    编辑Stage
                  </a-button>
                  <a-button type="primary" size="small" ghost @click="handleEditEnvironment(version)">
                    编辑Environment
                  </a-button>
                  <a-button
                    v-if="!version.is_latest"
                    type="primary"
                    size="small"
                    danger
                    :loading="deletingId === version.id"
                    @click="handleDeleteVersion(version)"
                  >
                    删除
                  </a-button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </a-spin>
    </div>

    <!-- 版本详情抽屉（只读，展示完整 Pipeline） -->
    <Drawer
      v-model:open="detailDrawerVisible"
      :title="`版本 ${currentDetailVersion?.version}`"
      :width="800"
    >
      <template #extra>
        <a-button @click="detailDrawerVisible = false">关闭</a-button>
      </template>

      <a-spin :spinning="detailLoading">
        <div v-if="currentDetailVersion" class="detail-content">
          <!-- 元信息 -->
          <div class="detail-section">
            <div class="info-grid">
              <div class="info-item">
                <span class="info-label">状态</span>
                <span class="info-value">
                  <a-tag :color="currentDetailVersion.status === 1 ? 'success' : 'default'">
                    {{ currentDetailVersion.status === 1 ? '启用' : '禁用' }}
                  </a-tag>
                  <a-tag v-if="currentDetailVersion.is_latest" color="blue">最新</a-tag>
                </span>
              </div>
              <div class="info-item">
                <span class="info-label">创建时间</span>
                <span class="info-value">{{ formatTime(currentDetailVersion.create_time) }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">创建者</span>
                <span class="info-value">{{ currentDetailVersion.creator || '系统' }}</span>
              </div>
            </div>
          </div>

          <!-- 变更说明 -->
          <div class="detail-section">
            <div class="section-title">变更说明</div>
            <div class="change-log-box">{{ currentDetailVersion.change_log || '无' }}</div>
          </div>

          <!-- 完整 Pipeline（Jenkinsfile） -->
          <div class="detail-section">
            <div class="section-title">完整 Pipeline（Jenkinsfile）</div>
            <div class="code-viewer">
              <pre><code>{{ currentDetailVersion.content }}</code></pre>
            </div>
          </div>
        </div>
      </a-spin>
    </Drawer>

    <!-- Stage 编辑弹窗 -->
    <AModal
      v-model:open="stageEditorVisible"
      title="编辑 Stage"
      :width="800"
      :confirm-loading="stageSaving"
      @ok="handleSaveStage"
    >
      <Alert type="info" class="mb-4" banner>
        <template #message>
          编辑后将自动创建新版本（版本号自动递增），原版本不受影响
        </template>
      </Alert>

      <div class="stage-selector mb-4">
        <label class="form-label">选择 Stage：</label>
        <Select
          v-model:value="currentStageName"
          style="width: 200px"
          @change="onStageChange"
        >
          <SelectOption v-for="stage in availableStages" :key="stage.name" :value="stage.name">
            {{ stage.name }}
          </SelectOption>
        </Select>
      </div>
      
      <div class="editor-container">
        <div class="editor-toolbar">
          <span class="editor-title">{{ currentStageName }} - Steps</span>
        </div>
        <textarea
          v-model="currentStageScript"
          class="code-editor"
          style="min-height: 300px"
          spellcheck="false"
        />
      </div>
    </AModal>

    <!-- Environment 编辑弹窗 -->
    <AModal
      v-model:open="envEditorVisible"
      title="编辑 Environment"
      :width="800"
      :confirm-loading="envSaving"
      @ok="handleSaveEnvironment"
    >
      <Alert type="info" class="mb-4" banner>
        <template #message>
          编辑后将自动创建新版本（版本号自动递增），原版本不受影响
        </template>
      </Alert>

      <div class="editor-container">
        <div class="editor-toolbar">
          <span class="editor-title">Environment 变量</span>
        </div>
        <textarea
          v-model="currentEnvContent"
          class="code-editor"
          style="min-height: 300px"
          spellcheck="false"
        />
      </div>
    </AModal>

    <!-- 版本对比弹窗 -->
    <AModal
      v-model:open="compareVisible"
      title="版本对比"
      :width="1100"
      :footer="null"
    >
      <div class="compare-selector mb-4">
        <a-space size="large">
          <div>
            <label class="form-label">旧版本：</label>
            <Select v-model:value="compareVersions.from" style="width: 200px" @change="loadCompareVersions">
              <SelectOption v-for="v in versionList" :key="v.id" :value="String(v.id)">
                {{ v.version }} {{ v.is_latest ? '(最新)' : '' }}
              </SelectOption>
            </Select>
          </div>
          <div>→</div>
          <div>
            <label class="form-label">新版本：</label>
            <Select v-model:value="compareVersions.to" style="width: 200px" @change="loadCompareVersions">
              <SelectOption v-for="v in versionList" :key="v.id" :value="String(v.id)">
                {{ v.version }} {{ v.is_latest ? '(最新)' : '' }}
              </SelectOption>
            </Select>
          </div>
          <a-button @click="compareWithPrev">与上一版本对比</a-button>
        </a-space>
      </div>

      <div v-if="compareFromVersion && compareToVersion" class="compare-result">
        <!-- 差异图例 -->
        <div class="diff-legend mb-2">
          <span class="legend-item">
            <span class="legend-color removed"></span> 删除的行
          </span>
          <span class="legend-item">
            <span class="legend-color added"></span> 新增的行
          </span>
          <span class="legend-item">
            <span class="legend-color unchanged"></span> 未变化的行
          </span>
        </div>

        <!-- 统一的差异视图 -->
        <div class="diff-container">
          <div class="diff-header">
            <div class="diff-col-header">
              <span class="version-label">{{ compareFromVersion.version }}</span>
              <span class="change-log-badge">{{ compareFromVersion.change_log || '无变更说明' }}</span>
            </div>
            <div class="diff-col-header">
              <span class="version-label">{{ compareToVersion.version }}</span>
              <span class="change-log-badge">{{ compareToVersion.change_log || '无变更说明' }}</span>
            </div>
          </div>
          <div class="diff-body">
            <div
              v-for="(line, index) in computeDiffLines(compareFromVersion.content || '', compareToVersion.content || '')"
              :key="index"
              class="diff-row"
              :class="line.type"
            >
              <div class="diff-cell diff-old">
                <span class="line-num">{{ line.oldLine || '' }}</span>
                <span class="line-content">{{ line.type === 'added' ? '' : line.content }}</span>
              </div>
              <div class="diff-cell diff-new">
                <span class="line-num">{{ line.newLine || '' }}</span>
                <span class="line-content">{{ line.type === 'removed' ? '' : line.content }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </AModal>
  </Modal>
</template>

<style scoped>
/* 头部 */
.version-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 8px;
  margin-bottom: 20px;
  color: #fff;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 20px;
}

.template-info {
  display: flex;
  align-items: baseline;
  gap: 10px;
}

.template-name {
  font-size: 18px;
  font-weight: 600;
}

.template-code {
  font-size: 13px;
  opacity: 0.8;
  font-family: monospace;
}

.version-count {
  font-size: 13px;
  opacity: 0.9;
  padding: 4px 12px;
  background: rgba(255,255,255,0.2);
  border-radius: 12px;
}

.header-right {
  display: flex;
  gap: 10px;
}

/* 版本列表 */
.version-list {
  min-height: 400px;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 16px;
}

.empty-text {
  font-size: 16px;
  color: #999;
  margin-bottom: 20px;
}

/* 时间线布局 */
.version-timeline {
  padding-left: 10px;
}

.version-card {
  display: flex;
  margin-bottom: 0;
  position: relative;
}

.timeline-indicator {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 30px;
  margin-right: 16px;
}

.timeline-dot {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 3px solid #fff;
  box-shadow: 0 0 0 2px currentColor;
  flex-shrink: 0;
  z-index: 1;
}

.timeline-line {
  width: 2px;
  flex: 1;
  background: #e8e8e8;
  margin: 4px 0;
}

.version-card.is-latest .timeline-dot {
  box-shadow: 0 0 0 2px #52c41a, 0 0 12px rgba(82, 196, 26, 0.4);
}

/* 版本卡片 */
.card-content {
  flex: 1;
  background: #fff;
  border-radius: 8px;
  border: 1px solid #e8e8e8;
  margin-bottom: 16px;
  overflow: hidden;
  transition: all 0.3s;
}

.card-content:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  border-color: #d9d9d9;
}

.version-card.is-latest .card-content {
  border-color: #52c41a;
  background: linear-gradient(to right, #f6ffed, #fff);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid #f0f0f0;
  background: #fafafa;
}

.version-card.is-latest .card-header {
  background: linear-gradient(to right, #f6ffed, #fafafa);
}

.version-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.version-number {
  font-size: 18px;
  font-weight: 600;
  font-family: 'SF Mono', 'Monaco', monospace;
  color: #262626;
}

.version-time {
  font-size: 12px;
  color: #8c8c8c;
}

.card-body {
  padding: 12px 16px;
}

.change-log {
  font-size: 14px;
  color: #595959;
}

.log-label {
  color: #8c8c8c;
  margin-right: 8px;
}

.log-content {
  word-break: break-all;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 16px;
  border-top: 1px solid #f0f0f0;
  background: #fafafa;
}

.creator {
  font-size: 12px;
  color: #8c8c8c;
}

.footer-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

/* 创建视图 */
.create-view {
  padding: 20px;
}

.create-header {
  margin-bottom: 20px;
}

.create-form {
  background: #fafafa;
  border-radius: 8px;
  padding: 20px;
}

.form-row {
  display: flex;
  gap: 20px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.form-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.form-label {
  font-weight: 500;
  color: #262626;
  white-space: nowrap;
}

.form-label.required::after {
  content: '*';
  color: #ff4d4f;
  margin-left: 4px;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #e8e8e8;
}

/* 编辑器 */
.editor-container {
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  overflow: hidden;
  background: #1e1e1e;
}

.editor-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: #2d2d2d;
  border-bottom: 1px solid #3d3d3d;
}

.editor-title {
  color: #e0e0e0;
  font-weight: 500;
}

.editor-actions {
  display: flex;
  gap: 8px;
}

.editor-body {
  padding: 0;
}

.code-editor {
  width: 100%;
  min-height: 400px;
  padding: 16px;
  border: none;
  outline: none;
  background: #1e1e1e;
  color: #d4d4d4;
  font-family: 'SF Mono', 'Menlo', 'Monaco', 'Consolas', monospace;
  font-size: 13px;
  line-height: 1.6;
  resize: vertical;
}

.code-editor::placeholder {
  color: #6a6a6a;
}

/* 详情抽屉 */
.detail-content {
  padding: 0;
}

.detail-section {
  margin-bottom: 24px;
}

.section-title {
  font-size: 15px;
  font-weight: 600;
  color: #262626;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #f0f0f0;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-label {
  font-size: 12px;
  color: #8c8c8c;
}

.info-value {
  font-size: 14px;
  color: #262626;
}

.change-log-box {
  padding: 12px 16px;
  background: #f6f6f6;
  border-radius: 6px;
  font-size: 14px;
  color: #595959;
}

.code-viewer {
  background: #1e1e1e;
  border-radius: 6px;
  overflow: auto;
  max-height: 500px;
}

.code-viewer pre {
  margin: 0;
  padding: 16px;
}

.code-viewer code {
  font-family: 'SF Mono', 'Menlo', 'Monaco', 'Consolas', monospace;
  font-size: 13px;
  line-height: 1.6;
  color: #d4d4d4;
  white-space: pre;
}

/* 差异对比 */
.diff-legend {
  display: flex;
  gap: 20px;
  padding: 8px 12px;
  background: #f5f5f5;
  border-radius: 4px;
  font-size: 12px;
  color: #666;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.legend-color {
  width: 16px;
  height: 4px;
  border-radius: 2px;
}

.legend-color.removed {
  background: #ffa39e;
}

.legend-color.added {
  background: #b7eb8f;
}

.legend-color.unchanged {
  background: #e8e8e8;
}

.diff-container {
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  overflow: hidden;
}

.diff-header {
  display: grid;
  grid-template-columns: 1fr 1fr;
  background: #fafafa;
  border-bottom: 1px solid #d9d9d9;
}

.diff-col-header {
  padding: 10px 16px;
  border-right: 1px solid #d9d9d9;
  display: flex;
  align-items: center;
  gap: 10px;
}

.diff-col-header:last-child {
  border-right: none;
}

.change-log-badge {
  font-size: 12px;
  color: #8c8c8c;
  background: #f0f0f0;
  padding: 2px 8px;
  border-radius: 10px;
}

.diff-body {
  max-height: 500px;
  overflow: auto;
  font-family: 'SF Mono', 'Menlo', 'Monaco', 'Consolas', monospace;
  font-size: 12px;
}

.diff-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
}

.diff-row.removed .diff-old {
  background: #fff1f0;
}

.diff-row.removed .diff-old .line-content {
  background: #ffa39e;
}

.diff-row.added .diff-new {
  background: #f6ffed;
}

.diff-row.added .diff-new .line-content {
  background: #b7eb8f;
}

.diff-cell {
  display: flex;
  min-height: 22px;
  border-right: 1px solid #e8e8e8;
  border-bottom: 1px solid #f0f0f0;
}

.diff-cell:last-child {
  border-right: none;
}

.line-num {
  width: 40px;
  min-width: 40px;
  padding: 0 8px;
  text-align: right;
  color: #999;
  background: #fafafa;
  user-select: none;
  border-right: 1px solid #e8e8e8;
}

.line-content {
  flex: 1;
  padding: 0 12px;
  white-space: pre;
  overflow-x: auto;
  color: #333;
}

/* 响应式 */
@media (max-width: 768px) {
  .version-header {
    flex-direction: column;
    gap: 12px;
  }
  
  .header-left, .header-right {
    width: 100%;
    justify-content: center;
  }
  
  .info-grid {
    grid-template-columns: 1fr;
  }
  
  .compare-grid {
    grid-template-columns: 1fr;
  }
}
</style>
