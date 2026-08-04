<script lang="ts" setup>
import type { ApprovalApi } from '#/api/release';

import { computed, ref } from 'vue';

import { useVbenDrawer } from '@vben/common-ui';

import {
  Alert,
  Button,
  Empty,
  Input,
  message,
  Progress,
  Spin,
  Steps,
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

// Steps 的子组件 Step 需通过 Steps.Step 引用（兼容 ant-design-vue 各版本导出）
const Step = Steps.Step;

const emit = defineEmits<{
  success: [];
}>();

const [Drawer, drawerApi] = useVbenDrawer({
  onConfirm: handleConfirm,
});

// 发布记录（用于显示摘要 + 判断当前用户是否可审批）
const releaseRecord = ref<ReleaseRecord | null>(null);
// 审批进度数据
const progress = ref<ApprovalApi.ApprovalProgress | null>(null);
const loading = ref(false);

// 审批意见
const comment = ref('');
// 操作类型：approve / reject（仅待审批状态可用）
const actionType = ref<'approve' | 'reject'>('approve');
const submitting = ref(false);

// 作用域中文映射
const scopeLabelMap: Record<string, string> = {
  application: '应用级',
  project: '项目级',
  global: '全局',
};

// 规则类型中文映射
const ruleTypeLabelMap: Record<string, string> = {
  single: '单人审批',
  any: '任意一人审批',
  all: '全部审批',
  sequential: '顺序审批',
};

// 是否处于待审批状态（可执行审批操作）
const canApprove = computed(
  () => releaseRecord.value?.status === 'approval_pending',
);

// 进度百分比
const progressPercent = computed(() => {
  if (!progress.value || !progress.value.required_count) return 0;
  return Math.round(
    (progress.value.approved_count / progress.value.required_count) * 100,
  );
});

// 是否为顺序审批
const isSequential = computed(
  () => progress.value?.rule_type === 'sequential',
);

// 当前节点文案
const stageText = computed(() => {
  if (!progress.value) return '';
  const { approved_count, required_count, current_stage, total_stage } =
    progress.value;
  if (isSequential.value && total_stage) {
    return `第 ${current_stage} / ${total_stage} 节点（已通过 ${approved_count}/${required_count}）`;
  }
  return `已通过 ${approved_count} / ${required_count}`;
});

// Steps 当前节点（顺序审批时使用）
const currentStep = computed(() => {
  if (!progress.value || !isSequential.value) return 0;
  const approved = progress.value.approved_count ?? 0;
  // 已完成数量即为当前节点索引（0-based）
  return Math.min(approved, (progress.value.total_stage ?? 1) - 1);
});

// 审批意见是否必填（拒绝时必填）
const commentRequired = computed(() => actionType.value === 'reject');

// 对外暴露的方法：open(record, presetAction?)
// presetAction 用于"通过/拒绝"按钮直接打开抽屉并预设操作类型
function open(record: ReleaseRecord, presetAction?: 'approve' | 'reject') {
  releaseRecord.value = record;
  comment.value = '';
  actionType.value = presetAction ?? 'approve';
  progress.value = null;
  drawerApi.open();
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

// 切换操作类型
function switchAction(type: 'approve' | 'reject') {
  actionType.value = type;
}

// 确认提交审批
async function handleConfirm() {
  if (!releaseRecord.value) return false;

  // 拒绝时审批意见必填
  if (commentRequired.value && !comment.value.trim()) {
    message.warning('请输入拒绝原因');
    return false;
  }

  submitting.value = true;
  try {
    if (actionType.value === 'approve') {
      const result = await approveRelease(releaseRecord.value.id, {
        comment: comment.value,
      });
      // result 为后端返回的 data 字段：{status, result, approved_count, ...}
      const resResult = (result as any)?.result;
      if (resResult === 'pending') {
        // 还需其他审批人：不关闭抽屉，重新加载进度
        message.success('已记录您的审批，等待其他审批人');
        await loadProgress(releaseRecord.value.id);
        // 更新本地 record 状态（避免 canApprove 计算属性过期）
        if (releaseRecord.value) {
          releaseRecord.value = {
            ...releaseRecord.value,
            status: (result as any)?.status || 'approval_pending',
          };
        }
        return false;
      }
      message.success('审批通过');
    } else {
      await rejectRelease(releaseRecord.value.id, {
        comment: comment.value,
      });
      message.success('已拒绝发布');
    }

    drawerApi.close();
    emit('success');
    return true;
  } catch (error: any) {
    // errorMessageResponseInterceptor 已自动显示后端错误 message，
    // 此处仅在无 message 时补充提示
    const errMsg =
      error?.response?.data?.error || error?.response?.data?.message;
    if (!errMsg) {
      message.error('操作失败');
    }
    return false;
  } finally {
    submitting.value = false;
  }
}

// 暴露方法
defineExpose({ open });
</script>

<template>
  <Drawer
    :footer="canApprove"
    :title="canApprove ? '审批处理' : '审批详情'"
    width="640px"
    :loading="submitting"
    :confirm-text="actionType === 'approve' ? '确认通过' : '确认拒绝'"
  >
    <div v-if="releaseRecord" class="approval-detail">
      <!-- 发布摘要 -->
      <Alert type="info" show-icon style="margin-bottom: 16px;">
        <template #message>
          <div class="info-content">
            <div>
              <strong>应用：</strong>{{ releaseRecord.application_name }}
            </div>
            <div><strong>分支：</strong>{{ releaseRecord.branch }}</div>
            <div>
              <strong>环境：</strong>{{ releaseRecord.environment_display }}
            </div>
            <div><strong>发布人：</strong>{{ releaseRecord.released_by }}</div>
            <div>
              <strong>发布状态：</strong>{{ releaseRecord.status_display }}
            </div>
            <div v-if="releaseRecord.remark" class="remark-row">
              <strong>发布说明：</strong>
              <span class="remark-text">{{ releaseRecord.remark }}</span>
            </div>
          </div>
        </template>
      </Alert>

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
              <span class="rule-value">
                {{
                  progress.rule_type_display ||
                  ruleTypeLabelMap[progress.rule_type || ''] ||
                  progress.rule_type ||
                  '-'
                }}
              </span>
            </div>
            <div v-if="progress.deadline" class="rule-row">
              <span class="rule-label">截止时间：</span>
              <span class="rule-value">{{ progress.deadline }}</span>
            </div>
          </div>

          <!-- 节点进度 -->
          <div class="section">
            <div class="section-title">审批节点</div>

            <!-- 顺序审批：使用 Steps 直观展示节点流转 -->
            <Steps
              v-if="isSequential && progress.total_stage"
              :current="currentStep"
              size="small"
              style="margin-bottom: 12px;"
            >
              <Step
                v-for="(item, idx) in progress.approvers"
                :key="idx"
                :title="item.username"
                :description="`节点 ${idx + 1}`"
              />
            </Steps>

            <!-- 其他类型：使用进度条 -->
            <Progress
              v-else
              :percent="progressPercent"
              :status="
                progress.approved_count >= progress.required_count
                  ? 'success'
                  : 'active'
              "
            />
            <div class="stage-text">{{ stageText }}</div>
          </div>

          <!-- 当前待审批人 -->
          <div
            v-if="progress.current_approver_names?.length"
            class="section"
          >
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

          <!-- 全部审批人列表（已通过 / 待审批） -->
          <div
            v-if="progress.approvers?.length && !isSequential"
            class="section"
          >
            <div class="section-title">审批人列表</div>
            <div class="approver-list">
              <template v-for="a in progress.approvers" :key="a.user_id">
                <Tag
                  v-if="
                    progress.approved_approvers?.some(
                      (p) => p.user_id === a.user_id,
                    )
                  "
                  color="success"
                  style="margin-right: 8px; margin-bottom: 4px;"
                >
                  {{ a.username }}（已通过）
                </Tag>
                <Tag
                  v-else
                  color="default"
                  style="margin-right: 8px; margin-bottom: 4px;"
                >
                  {{ a.username }}（待审批）
                </Tag>
              </template>
            </div>
          </div>

          <!-- 审批历史时间线 -->
          <div class="section">
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
                    <span class="history-action">{{
                      item.action_display || item.action
                    }}</span>
                    <span class="history-approver">{{
                      item.approver_name
                    }}</span>
                    <span v-if="item.acted_at" class="history-time">{{
                      item.acted_at
                    }}</span>
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

      <!-- 审批操作区（仅待审批状态显示） -->
      <template v-if="canApprove">
        <!-- 操作类型切换 -->
        <div class="action-switch">
          <Button
            :type="actionType === 'approve' ? 'primary' : 'default'"
            size="small"
            @click="switchAction('approve')"
          >
            通过
          </Button>
          <Button
            :type="actionType === 'reject' ? 'primary' : 'default'"
            :danger="actionType === 'reject'"
            size="small"
            style="margin-left: 8px;"
            @click="switchAction('reject')"
          >
            拒绝
          </Button>
        </div>

        <!-- 拒绝提示 -->
        <Alert
          v-if="actionType === 'reject'"
          type="warning"
          show-icon
          style="margin-top: 12px; margin-bottom: 12px;"
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
            :placeholder="
              actionType === 'approve'
                ? '请输入审批意见（可选）'
                : '请输入拒绝原因（必填）'
            "
            :rows="4"
            show-count
            :maxlength="512"
          />
        </div>
      </template>
    </div>
  </Drawer>
</template>

<style scoped>
.approval-detail {
  padding: 0 16px;
}

.info-content {
  line-height: 1.8;
}

.remark-row {
  margin-top: 4px;
  padding-top: 4px;
  border-top: 1px dashed #e8e8e8;
}

.remark-text {
  white-space: pre-wrap;
  word-break: break-all;
  color: #333;
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

.section {
  margin-bottom: 20px;
}

.section-title {
  font-weight: 500;
  margin-bottom: 8px;
  color: #333;
  border-left: 3px solid #1890ff;
  padding-left: 8px;
}

.stage-text {
  margin-top: 8px;
  color: #666;
  font-size: 13px;
}

.approver-list {
  line-height: 2;
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

.action-switch {
  margin-top: 16px;
  padding: 12px;
  background: #fafafa;
  border-radius: 4px;
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
