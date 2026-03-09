<script lang="ts" setup>
import { ref, watch, onUnmounted } from 'vue';
import { useVbenModal } from '@vben/common-ui';
import { Badge, Button, Spin, Tag, Tooltip } from 'ant-design-vue';
import { getBuildLogs, getReleaseDetail, RELEASE_STATUS_MAP } from '#/api/release';

const emit = defineEmits<{
  success: [];
}>();

const [Modal, modalApi] = useVbenModal({
  onConfirm: handleConfirm,
});

// 发布记录
const releaseId = ref<number | null>(null);
const releaseInfo = ref<any>(null);
const loading = ref(false);

// 日志内容
const logContent = ref('');
const logLoading = ref(false);
const autoRefresh = ref(false);
let refreshTimer: ReturnType<typeof setInterval> | null = null;

// 状态颜色映射
const statusColorMap: Record<string, string> = {
  pending: 'default',
  approval_pending: 'warning',
  approved: 'success',
  rejected: 'error',
  building: 'processing',
  build_success: 'success',
  build_failed: 'error',
  deploying: 'processing',
  deployed: 'success',
  rollback: 'warning',
  cancelled: 'default',
};

// 是否可以刷新日志
const canRefresh = ref(true);

// 监听弹窗打开
watch(
  () => modalApi.isOpen?.value,
  (isOpen) => {
    if (isOpen) {
      const data = modalApi.getData<{ id: number }>();
      if (data?.id) {
        releaseId.value = data.id;
        loadReleaseInfo();
        loadLogs();
      }
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
    if (res.status === 'building') {
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
    const logContainer = document.querySelector('.log-content');
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

// 关闭弹窗
function handleConfirm() {
  stopAutoRefresh();
  modalApi.close();
  return true;
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
</script>

<template>
  <Modal
    :footer="true"
    title="构建日志"
    width="900px"
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
        <div class="info-row">
          <div class="info-item">
            <span class="label">发布人：</span>
            <span class="value">{{ releaseInfo.released_by }}</span>
          </div>
          <div class="info-item">
            <span class="label">发布时间：</span>
            <span class="value">{{ releaseInfo.create_time }}</span>
          </div>
        </div>
      </div>

      <a-divider style="margin: 12px 0;" />

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

      <!-- 日志内容 -->
      <div class="log-container">
        <Spin :spinning="logLoading">
          <pre class="log-content">{{ logContent || '暂无日志' }}</pre>
        </Spin>
      </div>
    </Spin>
  </Modal>
</template>

<style scoped>
.release-info {
  background: #f5f5f5;
  padding: 12px 16px;
  border-radius: 4px;
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
  color: #666;
  min-width: 70px;
}

.info-item .value {
  font-weight: 500;
}

.log-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding: 8px 12px;
  background: #fafafa;
  border-radius: 4px;
}

.toolbar-left,
.toolbar-right {
  display: flex;
  align-items: center;
}

.log-container {
  background: #1e1e1e;
  border-radius: 4px;
  max-height: 500px;
  overflow: auto;
}

.log-content {
  color: #d4d4d4;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.5;
  margin: 0;
  padding: 12px;
  white-space: pre-wrap;
  word-break: break-all;
  min-height: 300px;
}

/* 自定义滚动条 */
.log-container::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

.log-container::-webkit-scrollbar-track {
  background: #2d2d2d;
}

.log-container::-webkit-scrollbar-thumb {
  background: #555;
  border-radius: 4px;
}

.log-container::-webkit-scrollbar-thumb:hover {
  background: #666;
}
</style>
