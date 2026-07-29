<script lang="ts" setup>
import type { EnvironmentStrategyApi } from '#/api/release';

import { ref, computed } from 'vue';

import { useVbenModal } from '@vben/common-ui';

import { message } from 'ant-design-vue';

import {
  createStrategy,
  getStrategyDetail,
  updateStrategy,
} from '#/api/release';
import { getEnvironmentOptions } from '../data';

const emit = defineEmits(['success']);

const [Modal, modalApi] = useVbenModal({
  async onConfirm() {
    await handleSubmit();
  },
  async onOpenChange(isOpen) {
    if (isOpen) {
      const data = modalApi.getData<EnvironmentStrategyApi.Strategy>();
      if (data?.id) {
        await loadData(data.id);
      } else {
        formData.value = {
          name: '',
          code: '',
          environment: 'test',
          requires_approval: false,
          auto_deploy: false,
          description: '',
          is_default: false,
          status: 1,
        };
      }
    }
  },
});

const formData = ref<Partial<EnvironmentStrategyApi.Strategy>>({
  name: '',
  code: '',
  environment: 'test',
  requires_approval: false,
  auto_deploy: false,
  description: '',
  is_default: false,
  status: 1,
});

const isEdit = computed(() => !!formData.value.id);
const modalTitle = computed(() => (isEdit.value ? '编辑策略' : '创建策略'));

// 加载数据
async function loadData(id: number) {
  try {
    const result = await getStrategyDetail(id);
    formData.value = result;
  } catch {
    message.error('加载数据失败');
  }
}

// 提交表单
async function handleSubmit() {
  try {
    if (isEdit.value) {
      await updateStrategy(formData.value.id!, formData.value);
      message.success('更新成功');
    } else {
      await createStrategy(formData.value);
      message.success('创建成功');
    }
    modalApi.close();
    emit('success');
  } catch (error: any) {
    message.error(error?.message || '操作失败');
    throw error;
  }
}

const environmentOptions = getEnvironmentOptions();
</script>

<template>
  <Modal :title="modalTitle">
    <a-form
      :model="formData"
      :label-col="{ span: 5 }"
      :wrapper-col="{ span: 18 }"
    >
      <a-form-item
        label="策略名称"
        name="name"
        :rules="[{ required: true, message: '请输入策略名称' }]"
      >
        <a-input v-model:value="formData.name" placeholder="请输入策略名称" />
      </a-form-item>

      <a-form-item
        label="策略编码"
        name="code"
        :rules="[{ required: true, message: '请输入策略编码' }]"
      >
        <a-input
          v-model:value="formData.code"
          placeholder="如: test-integrated"
          :disabled="isEdit"
        />
      </a-form-item>

      <a-form-item
        label="环境"
        name="environment"
        :rules="[{ required: true, message: '请选择环境' }]"
      >
        <a-select
          v-model:value="formData.environment"
          :options="environmentOptions"
          placeholder="请选择环境"
        />
      </a-form-item>

      <a-form-item label="需要审批" name="requires_approval">
        <a-switch v-model:checked="formData.requires_approval" />
      </a-form-item>

      <a-form-item label="自动部署" name="auto_deploy">
        <a-switch v-model:checked="formData.auto_deploy" />
      </a-form-item>

      <a-form-item label="默认策略" name="is_default">
        <a-switch v-model:checked="formData.is_default" />
      </a-form-item>

      <a-form-item label="描述" name="description">
        <a-textarea
          v-model:value="formData.description"
          placeholder="请输入策略描述"
          :rows="3"
        />
      </a-form-item>

      <a-form-item label="状态" name="status">
        <a-radio-group v-model:value="formData.status">
          <a-radio :value="1">启用</a-radio>
          <a-radio :value="0">禁用</a-radio>
        </a-radio-group>
      </a-form-item>
    </a-form>
  </Modal>
</template>
