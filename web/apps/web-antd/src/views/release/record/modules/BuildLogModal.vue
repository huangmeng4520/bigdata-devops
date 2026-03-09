<script lang="ts" setup>
import { ref, watch, computed, onUnmounted } from 'vue';
import { useVbenModal } from '@vben/common-ui';
import { Badge, Button, Divider, Spin, Tag, Tooltip } from 'ant-design-vue';
import { getBuildLogs, getReleaseDetail, RELEASE_STATUS_MAP } from '#/api/release/record';

// 发布记录
const releaseId = ref<number | null>(null);
const releaseInfo = ref<any>(null);
const loading = ref(false);

// 日志内容
const logContent = ref('');
const logLoading = ref(false);
const autoRefresh = ref(false);
let refreshTimer: ReturnType<typeof setInterval> | null = null;

// 日志行数据
const logLines = computed(() => {
  if (!logContent.value || logContent.value === '暂无构建日志' || logContent.value === '加载日志失败') {
    return [];
  }
  return logContent.value.split('\n');
});

// 关闭弹窗
function handleConfirm() {
  stopAutoRefresh();
  modalApi.close();
  return true;
}

const [Modal, modalApi] = useVbenModal({
  onConfirm: handleConfirm,
});

// 对外暴露的方法
function open(id: number) {
  releaseId.value = id;
  modalApi.open();
}

// 监听弹窗打开
watch(
  () => modalApi.isOpen?.value,
  (isOpen) => {
    if (isOpen && releaseId.value) {
      loadReleaseInfo();
      loadLogs();
    } else {
      stopAutoRefresh();
    }
  },
);

// 加载发布信息
async function loadReleaseInfo() {
  if (!releaseId.value) return;

  loading.value = true;
  try {
    const res = await getReleaseDetail(releaseId.value);
    releaseInfo.value = res;

    // 如果是构建中状态，自动刷新
    if (res?.status === 'building') {
      autoRefresh.value = true;
      startAutoRefresh();
    }
  } catch (error) {
    console.error('加载发布信息失败', error);
  } finally {
    loading.value = false;
  }
}

// 加载日志
async function loadLogs() {
  if (!releaseId.value) return;

  logLoading.value = true;
  try {
    const res = await getBuildLogs(releaseId.value);
    if (res && res.length > 0) {
      // 合并所有日志
      logContent.value = res.map((log: any) => log.log_content).join('\n');
    } else {
      logContent.value = '暂无构建日志';
    }

    // 滚动到底部
    scrollToBottom();
  } catch (error) {
    console.error('加载日志失败', error);
    logContent.value = '加载日志失败';
  } finally {
    logLoading.value = false;
  }
}

// 滚动到底部
function scrollToBottom() {
  setTimeout(() => {
    const logContainer = document.querySelector('.terminal-body');
    if (logContainer) {
      logContainer.scrollTop = logContainer.scrollHeight;
    }
  }, 100);
}

// 开始自动刷新
function startAutoRefresh() {
  if (refreshTimer) return;
  refreshTimer = setInterval(() => {
    loadLogs();
    loadReleaseInfo();
  }, 3000);
}

// 停止自动刷新
function stopAutoRefresh() {
  if (refreshTimer) {
    clearInterval(refreshTimer);
    refreshTimer = null;
  }
  autoRefresh.value = false;
}

// 切换自动刷新
function toggleAutoRefresh() {
  if (autoRefresh.value) {
    stopAutoRefresh();
  } else {
    autoRefresh.value = true;
    startAutoRefresh();
  }
}

// 手动刷新
function handleRefresh() {
  loadLogs();
  loadReleaseInfo();
}

// 打开 Jenkins 构建页面
function openJenkinsBuild() {
  if (releaseInfo.value?.jenkins_build_url) {
    window.open(releaseInfo.value.jenkins_build_url, '_blank');
  }
}

// 组件卸载时清理定时器
onUnmounted(() => {
  stopAutoRefresh();
});

// 格式化持续时间
function formatDuration(ms: number | null): string {
  if (!ms) return '-';
  const seconds = Math.floor(ms / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);

  if (hours > 0) {
    return `${hours}h ${minutes % 60}m ${seconds % 60}s`;
  } else if (minutes > 0) {
    return `${minutes}m ${seconds % 60}s`;
  } else {
    return `${seconds}s`;
  }
}

// 解析 ANSI 颜色代码并高亮显示
function parseAnsiColors(text: string): string {
  // ANSI 颜色代码映射
  const ansiColors: Record<string, string> = {
    '30': '#4e4e4e',   // 黑色
    '31': '#ff6b6b',   // 红色
    '32': '#98c379',   // 绿色
    '33': '#e5c07b',   // 黄色
    '34': '#61afef',   // 蓝色
    '35': '#c678dd',   // 紫色
    '36': '#56b6c2',   // 青色
    '37': '#abb2bf',   // 白色
    '90': '#5c6370',   // 亮黑
    '91': '#e06c75',   // 亮红
    '92': '#98c379',   // 亮绿
    '93': '#e5c07b',   // 亮黄
    '94': '#61afef',   // 亮蓝
    '95': '#c678dd',   // 亮紫
    '96': '#56b6c2',   // 亮青
    '97': '#ffffff',   // 亮白
    '1': '',           // 粗体
    '0': '',           // 重置
  };

  // 移除 ANSI 控制序列并保留颜色信息
  let result = text;
  
  // 处理常见的 ANSI 转义序列
  const ansiRegex = /\x1b\[([0-9;]+)m/g;
  let match;
  let lastIndex = 0;
  let colorStack: string[] = [];
  let output = '';
  
  while ((match = ansiRegex.exec(result)) !== null) {
    output += result.slice(lastIndex, match.index);
    
    const codes = match[1].split(';');
    for (const code of codes) {
      if (code === '0') {
        // 重置
        if (colorStack.length > 0) {
          output += '</span>';
          colorStack.pop();
        }
        while (colorStack.length > 0) {
          output += '</span>';
          colorStack.pop();
        }
      } else if (ansiColors[code]) {
        const color = ansiColors[code];
        if (color) {
          output += `<span style="color: ${color}">`;
          colorStack.push(color);
        }
      }
    }
    lastIndex = match.index + match[0].length;
  }
  
  output += result.slice(lastIndex);
  
  // 关闭未关闭的标签
  while (colorStack.length > 0) {
    output += '</span>';
    colorStack.pop();
  }
  
  // 如果没有 ANSI 代码，返回原始文本
  if (!ansiRegex.test(text)) {
    return highlightKeywords(text);
  }
  
  return output;
}

// 高亮关键词
function highlightKeywords(text: string): string {
  // 转义 HTML
  let escaped = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
  
  // 高亮 ERROR
  escaped = escaped.replace(/\b(ERROR|FAILED|FAILURE|Error|Failed|Exception)\b/g, 
    '<span class="log-error">$1</span>');
  
  // 高亮 WARNING
  escaped = escaped.replace(/\b(WARNING|WARN|Warning)\b/g, 
    '<span class="log-warning">$1</span>');
  
  // 高亮 SUCCESS
  escaped = escaped.replace(/\b(SUCCESS|SUCCESSFUL|Success)\b/g, 
    '<span class="log-success">$1</span>');
  
  // 高亮 [Pipeline] 标记
  escaped = escaped.replace(/\[Pipeline\]/g, '<span class="log-pipeline">[Pipeline]</span>');
  
  // 高亮 stage 名称
  escaped = escaped.replace(/\{ \(([^)]+)\) \}/g, '{ <span class="log-stage">($1)</span> }');
  
  return escaped;
}

// 获取状态指示灯颜色
function getStatusIndicatorColor(status: string): string {
  const statusColors: Record<string, string> = {
    'building': '#61afef',
    'build_success': '#98c379',
    'build_failed': '#ff6b6b',
    'pending': '#abb2bf',
    'cancelled': '#5c6370',
  };
  return statusColors[status] || '#abb2bf';
}

// 暴露方法
defineExpose({ open });
</script>

<template>
  <Modal
    :footer="true"
    title="构建日志"
    width="950px"
    confirm-text="关闭"
  >
    <Spin :spinning="loading">
      <!-- 发布信息 -->
      <div v-if="releaseInfo" class="release-info">
        <div class="info-row">
          <div class="info-item">
            <span class="label">应用名称：</span>
            <span class="value">{{ releaseInfo.application_name }}</span>
          </div>
          <div class="info-item">
            <span class="label">发布分支：</span>
            <span class="value">
              <Tag color="blue">{{ releaseInfo.branch }}</Tag>
            </span>
          </div>
          <div class="info-item">
            <span class="label">目标环境：</span>
            <span class="value">{{ releaseInfo.environment_display }}</span>
          </div>
        </div>
        <div class="info-row">
          <div class="info-item">
            <span class="label">构建号：</span>
            <span class="value">
              <a
                v-if="releaseInfo.jenkins_build_url"
                @click="openJenkinsBuild"
                style="cursor: pointer; color: #1890ff;"
              >
                #{{ releaseInfo.jenkins_build_number }}
              </a>
              <span v-else>-</span>
            </span>
          </div>
          <div class="info-item">
            <span class="label">构建状态：</span>
            <span class="value">
              <Badge
                :status="releaseInfo.status === 'building' ? 'processing' : (releaseInfo.status === 'build_success' ? 'success' : 'error')"
                :text="RELEASE_STATUS_MAP[releaseInfo.status]?.text || releaseInfo.status"
              />
            </span>
          </div>
          <div class="info-item">
            <span class="label">构建耗时：</span>
            <span class="value">{{ formatDuration(releaseInfo.jenkins_build_duration) }}</span>
          </div>
        </div>
      </div>

      <!-- 日志操作栏 -->
      <div class="log-toolbar">
        <div class="toolbar-left">
          <Button
            type="link"
            size="small"
            @click="handleRefresh"
            :loading="logLoading"
          >
            刷新日志
          </Button>
          <Button
            type="link"
            size="small"
            @click="toggleAutoRefresh"
            :type="autoRefresh ? 'primary' : 'default'"
          >
            {{ autoRefresh ? '停止刷新' : '自动刷新' }}
          </Button>
          <Tag v-if="autoRefresh" color="processing" style="margin-left: 8px;">
            每 3 秒刷新中...
          </Tag>
        </div>
        <div class="toolbar-right">
          <Tooltip title="在新窗口打开 Jenkins 构建">
            <Button
              type="link"
              size="small"
              @click="openJenkinsBuild"
              :disabled="!releaseInfo?.jenkins_build_url"
            >
              打开 Jenkins
            </Button>
          </Tooltip>
        </div>
      </div>

      <!-- 终端风格日志容器 -->
      <div class="terminal-container">
        <!-- 终端头部 -->
        <div class="terminal-header">
          <div class="terminal-buttons">
            <span class="terminal-btn close"></span>
            <span class="terminal-btn minimize"></span>
            <span class="terminal-btn maximize"></span>
          </div>
          <div class="terminal-title">
            <span class="terminal-icon">⬡</span>
            <span>Jenkins Build Log</span>
            <span 
              class="status-indicator" 
              :style="{ backgroundColor: getStatusIndicatorColor(releaseInfo?.status) }"
            ></span>
          </div>
          <div class="terminal-actions">
            <span class="line-count" v-if="logLines.length">{{ logLines.length }} 行</span>
          </div>
        </div>
        
        <!-- 终端内容 -->
        <div class="terminal-body" ref="terminalBody">
          <Spin :spinning="logLoading" tip="加载日志中...">
            <!-- 有日志内容时显示 -->
            <template v-if="logLines.length > 0">
              <div 
                v-for="(line, index) in logLines" 
                :key="index" 
                class="log-line"
              >
                <span class="line-number">{{ String(index + 1).padStart(4, ' ') }}</span>
                <span class="line-content" v-html="highlightKeywords(line)"></span>
              </div>
            </template>
            <!-- 无日志时显示 -->
            <div v-else class="empty-log">
              <div class="empty-icon">📝</div>
              <div class="empty-text">{{ logContent || '暂无构建日志' }}</div>
            </div>
          </Spin>
        </div>
      </div>
    </Spin>
  </Modal>
</template>

<style scoped>
.release-info {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 14px 18px;
  border-radius: 8px;
  margin-bottom: 12px;
  color: #fff;
}

.info-row {
  display: flex;
  margin-bottom: 8px;
}

.info-row:last-child {
  margin-bottom: 0;
}

.info-item {
  flex: 1;
  display: flex;
  align-items: center;
}

.info-item .label {
  color: rgba(255, 255, 255, 0.8);
  min-width: 70px;
  font-size: 13px;
}

.info-item .value {
  font-weight: 500;
  color: #fff;
}

.info-item .value :deep(.ant-tag) {
  margin: 0;
}

.log-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding: 10px 14px;
  background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%);
  border-radius: 8px;
  border: 1px solid #e8e8e8;
}

.toolbar-left,
.toolbar-right {
  display: flex;
  align-items: center;
}

/* 终端容器 */
.terminal-container {
  border-radius: 10px;
  overflow: hidden;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
  border: 1px solid #333;
}

/* 终端头部 */
.terminal-header {
  background: linear-gradient(180deg, #3d3d3d 0%, #2d2d2d 100%);
  padding: 12px 16px;
  display: flex;
  align-items: center;
  border-bottom: 1px solid #1a1a1a;
}

.terminal-buttons {
  display: flex;
  gap: 8px;
}

.terminal-btn {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  cursor: pointer;
}

.terminal-btn.close {
  background: #ff5f56;
  border: 1px solid #e0443e;
}

.terminal-btn.minimize {
  background: #ffbd2e;
  border: 1px solid #dea123;
}

.terminal-btn.maximize {
  background: #27c93f;
  border: 1px solid #1aab29;
}

.terminal-title {
  flex: 1;
  text-align: center;
  color: #999;
  font-size: 13px;
  font-family: 'SF Mono', 'Consolas', monospace;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.terminal-icon {
  font-size: 14px;
}

.status-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.terminal-actions {
  min-width: 80px;
  text-align: right;
}

.line-count {
  color: #666;
  font-size: 11px;
  font-family: 'SF Mono', 'Consolas', monospace;
}

/* 终端内容 */
.terminal-body {
  background: #1a1a2e;
  max-height: 500px;
  overflow: auto;
  font-family: 'SF Mono', 'Fira Code', 'Consolas', 'Monaco', monospace;
  font-size: 12px;
  line-height: 1.6;
}

/* 日志行 */
.log-line {
  display: flex;
  padding: 0 4px;
  transition: background-color 0.15s;
}

.log-line:hover {
  background: rgba(255, 255, 255, 0.03);
}

.line-number {
  color: #4a4a6a;
  text-align: right;
  min-width: 45px;
  padding-right: 12px;
  user-select: none;
  border-right: 1px solid #2a2a4a;
  margin-right: 12px;
}

.line-content {
  color: #e0e0e0;
  white-space: pre;
  flex: 1;
  word-break: break-all;
}

/* 日志高亮 */
.line-content :deep(.log-error) {
  color: #ff6b6b;
  font-weight: 600;
}

.line-content :deep(.log-warning) {
  color: #e5c07b;
  font-weight: 500;
}

.line-content :deep(.log-success) {
  color: #98c379;
  font-weight: 500;
}

.line-content :deep(.log-pipeline) {
  color: #61afef;
  font-weight: 600;
}

.line-content :deep(.log-stage) {
  color: #c678dd;
  font-style: italic;
}

/* 空日志 */
.empty-log {
  padding: 60px 20px;
  text-align: center;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
  opacity: 0.5;
}

.empty-text {
  color: #666;
  font-size: 14px;
}

/* 滚动条样式 */
.terminal-body::-webkit-scrollbar {
  width: 10px;
  height: 10px;
}

.terminal-body::-webkit-scrollbar-track {
  background: #15152a;
}

.terminal-body::-webkit-scrollbar-thumb {
  background: #3a3a5a;
  border-radius: 5px;
  border: 2px solid #15152a;
}

.terminal-body::-webkit-scrollbar-thumb:hover {
  background: #4a4a7a;
}

.terminal-body::-webkit-scrollbar-corner {
  background: #15152a;
}

/* 加载动画 */
:deep(.ant-spin) {
  max-height: none;
}

:deep(.ant-spin-container) {
  display: block;
}

:deep(.ant-spin-nested-loading) {
  display: block;
}
</style>
