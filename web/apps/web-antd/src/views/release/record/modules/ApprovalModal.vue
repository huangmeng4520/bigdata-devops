<script lang="ts" setup>
import { ref } from 'vue';
import { useVbenModal } from '@vben/common-ui';
import { message, Input, Alert } from 'ant-design-vue';
import { approveRelease, rejectRelease, type ReleaseRecord } from '#/api/release/record';

const emit = defineEmits<{
  success: [];
}>();

const [Modal, modalApi] = useVbenModal({
  onConfirm: handleConfirm,
});

// 发布记录
const releaseRecord = ref<ReleaseRecord | null>(null);
const approvalType = ref<'approve' | 'reject'>('approve');

// 审批意见
const comment = ref('');

// 提交状态
const submitting = ref(false);

// 对外暴露的方法
function open(record: ReleaseRecord, type: 'approve' | 'reject') {
  releaseRecord.value = record;
  approvalType.value = type;
  comment.value = '';
  modalApi.open();
}

// 确认
async function handleConfirm() {
  if (!releaseRecord.value) return false;

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
    width="500px"
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

      <!-- 拒绝提示 -->
      <Alert
        v-if="approvalType === 'reject'"
        type="warning"
        show-icon
        style="margin-bottom: 16px;"
      >
        <template #message>
          拒绝后，该发布记录将被标记为已拒绝，发布人需要重新发起发布。
        </template>
      </Alert>

      <!-- 审批意见 -->
      <div class="form-item">
        <label>审批意见</label>
        <Input.TextArea
          v-model:value="comment"
          :placeholder="approvalType === 'approve' ? '请输入审批意见（可选）' : '请输入拒绝原因'"
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

.form-item {
  margin-bottom: 16px;
}

.form-item label {
  display: block;
  margin-bottom: 8px;
  font-weight: 500;
}
</style>
