<script lang="ts" setup>
import type { ApprovalApi } from '#/api/release';

import { computed, ref } from 'vue';

import { useVbenModal } from '@vben/common-ui';

import {
  Alert,
  Empty,
  Input,
  message,
  Progress,
  Spin,
  Tag,
  Timeline,
  TimelineItem,
} from 'ant-design-vue';

import {
  approveRelease,
  rejectRelease,
  type ReleaseRecord,
} from '#/api/release/record';
import { getApprovalProgress } from '#/api/release';

const emit = defineEmits<{
  success: [];
}>();

const [Modal, modalApi] = useVbenModal({
  onConfirm: handleConfirm,
});

// 发布记录
const releaseRecord = ref<ReleaseRecord | null>(null);
const approvalType = ref<'approve' | 'reject'>('approve');

// 审批进度
const progress = ref<ApprovalApi.ApprovalProgress | null>(null);
const loading = ref(false);

// 审批意见
const comment = ref('');

// 提交状态
const submitting = ref(false);

// 作用域中文映射
const scopeLabelMap: Record<string, string> = {
  application: '应用级',
  project: '项目级',
  global: '全局',
};

// 进度百分比
const progressPercent = computed(() => {
  if (!progress.value || !progress.value.required_count) return 0;
  return Math.round(
    (progress.value.approved_count / progress.value.required_count) * 100,
  );
});

// 审批意见是否必填（拒绝时必填）
const commentRequired = computed(() => approvalType.value === 'reject');

// 对外暴露的方法
function open(record: ReleaseRecord, type: 'approve' | 'reject') {
  releaseRecord.value = record;
  approvalType.value = type;
  comment.value = '';
  progress.value = null;
  modalApi.open();
  // 加载审批进度
  loadProgress(record.id);
}

// 加载审批进度
async function loadProgress(releaseId: number) {
  loading.value = true;
  try {
    const result = await getApprovalProgress(releaseId);
    progress.value = result || null;
  } catch (error) {
    console.error('加载审批进度失败', error);
    progress.value = null;
  } finally {
    loading.value = false;
  }
}

// 确认
async function handleConfirm() {
  if (!releaseRecord.value) return false;

  // 拒绝时审批意见必填
  if (commentRequired.value && !comment.value.trim()) {
    message.warning('请输入拒绝原因');
    return false;
  }

  submitting.value = true;
  try {
    if (approvalType.value === 'approve') {
      await approveRelease(releaseRecord.value.id, { comment: comment.value });
      message.success('审批通过');
    } else {
      await rejectRelease(releaseRecord.value.id, { comment: comment.value });
      message.success('已拒绝发布');
    }

    modalApi.close();
    emit('success');
    return true;
  } catch (error: any) {
    message.error(error?.response?.data?.error || '操作失败');
    return false;
  } finally {
    submitting.value = false;
  }
}

// 获取标题
function getTitle(): string {
  return approvalType.value === 'approve' ? '审批通过' : '审批拒绝';
}

// 暴露方法
defineExpose({ open });
</script>

<template>
  <Modal
    :footer="true"
    :title="getTitle()"
    width="640px"
    :loading="submitting"
  >
    <div v-if="releaseRecord" class="approval-form">
      <!-- 发布信息 -->
      <Alert type="info" show-icon style="margin-bottom: 16px;">
        <template #message>
          <div class="info-content">
            <div><strong>应用：</strong>{{ releaseRecord.application_name }}</div>
            <div><strong>分支：</strong>{{ releaseRecord.branch }}</div>
            <div><strong>环境：</strong>{{ releaseRecord.environment_display }}</div>
            <div><strong>发布人：</strong>{{ releaseRecord.released_by }}</div>
          </div>
        </template>
      </Alert>

      <!-- 审批进度 -->
      <Spin :spinning="loading">
        <template v-if="progress">
          <!-- 审批规则信息 -->
          <div class="rule-info">
            <div class="rule-row">
              <span class="rule-label">规则名称：</span>
              <span class="rule-value">{{ progress.rule_name || '-' }}</span>
              <Tag
                v-if="progress.scope"
                color="blue"
                style="margin-left: 8px;"
              >
                {{ scopeLabelMap[progress.scope] || progress.scope }}
              </Tag>
            </div>
            <div class="rule-row">
              <span class="rule-label">规则类型：</span>
              <span class="rule-value">{{ progress.rule_type_display || progress.rule_type || '-' }}</span>
            </div>
            <div v-if="progress.deadline" class="rule-row">
              <span class="rule-label">截止时间：</span>
              <span class="rule-value">{{ progress.deadline }}</span>
            </div>
          </div>

          <!-- 进度条 -->
          <div class="progress-section">
            <div class="progress-title">
              审批进度：已通过 {{ progress.approved_count }} / {{ progress.required_count }}
            </div>
            <Progress
              :percent="progressPercent"
              :status="
                progress.approved_count >= progress.required_count
                  ? 'success'
                  : 'active'
              "
            />
          </div>

          <!-- 当前待审批人 -->
          <div v-if="progress.current_approver_names?.length" class="current-approvers">
            <div class="section-title">当前待审批人</div>
            <div>
              <Tag
                v-for="(name, idx) in progress.current_approver_names"
                :key="idx"
                color="orange"
                style="margin-right: 8px; margin-bottom: 4px;"
              >
                {{ name }}
              </Tag>
            </div>
          </div>

          <!-- 审批历史时间线 -->
          <div class="history-section">
            <div class="section-title">审批历史</div>
            <Empty
              v-if="!progress.history || progress.history.length === 0"
              description="暂无审批记录"
            />
            <Timeline v-else>
              <TimelineItem
                v-for="(item, idx) in progress.history"
                :key="idx"
                :color="
                  item.action === 'approve'
                    ? 'green'
                    : item.action === 'reject'
                      ? 'red'
                      : 'blue'
                "
              >
                <div class="history-item">
                  <div class="history-header">
                    <span class="history-action">{{ item.action_display || item.action }}</span>
                    <span class="history-approver">{{ item.approver_name }}</span>
                    <span v-if="item.acted_at" class="history-time">{{ item.acted_at }}</span>
                  </div>
                  <div v-if="item.comment" class="history-comment">
                    {{ item.comment }}
                  </div>
                </div>
              </TimelineItem>
            </Timeline>
          </div>
        </template>

        <Empty v-else-if="!loading" description="暂无审批进度信息" />
      </Spin>

      <!-- 拒绝提示 -->
      <Alert
        v-if="approvalType === 'reject'"
        type="warning"
        show-icon
        style="margin-top: 16px; margin-bottom: 16px;"
      >
        <template #message>
          拒绝后，该发布记录将被标记为已拒绝，发布人需要重新发起发布。
        </template>
      </Alert>

      <!-- 审批意见 -->
      <div class="form-item">
        <label>
          审批意见
          <span v-if="commentRequired" class="required-mark">*</span>
        </label>
        <Input.TextArea
          v-model:value="comment"
          :placeholder="approvalType === 'approve' ? '请输入审批意见（可选）' : '请输入拒绝原因（必填）'"
          :rows="4"
          show-count
          :maxlength="512"
        />
      </div>
    </div>
  </Modal>
</template>

<style scoped>
.approval-form {
  padding: 0 16px;
}

.info-content {
  line-height: 1.8;
}

.rule-info {
  background: #fafafa;
  border: 1px solid #f0f0f0;
  border-radius: 4px;
  padding: 12px;
  margin-bottom: 16px;
}

.rule-row {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
  line-height: 1.8;
}

.rule-row:last-child {
  margin-bottom: 0;
}

.rule-label {
  color: #666;
  width: 80px;
  flex-shrink: 0;
}

.rule-value {
  font-weight: 500;
}

.progress-section {
  margin-bottom: 16px;
}

.progress-title {
  margin-bottom: 8px;
  font-weight: 500;
}

.current-approvers {
  margin-bottom: 16px;
}

.section-title {
  font-weight: 500;
  margin-bottom: 8px;
  color: #333;
}

.history-section {
  margin-bottom: 16px;
}

.history-item {
  line-height: 1.6;
}

.history-header {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.history-action {
  font-weight: 500;
  color: #1890ff;
}

.history-approver {
  color: #333;
}

.history-time {
  color: #999;
  font-size: 12px;
}

.history-comment {
  color: #666;
  margin-top: 4px;
  padding: 4px 8px;
  background: #f5f5f5;
  border-radius: 2px;
  font-size: 13px;
}

.form-item {
  margin-bottom: 16px;
}

.form-item label {
  display: block;
  margin-bottom: 8px;
  font-weight: 500;
}

.required-mark {
  color: #ff4d4f;
  margin-left: 4px;
}
</style>
