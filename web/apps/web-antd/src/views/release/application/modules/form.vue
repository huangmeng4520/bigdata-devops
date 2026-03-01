<script lang="ts" setup>
import type { ReleaseApplicationApi } from '#/api/release';

import { computed, ref } from 'vue';

import { useVbenModal } from '@vben/common-ui';

import { Button } from 'ant-design-vue';

import { useVbenForm } from '#/adapter/form';
import { createApplication, updateApplication } from '#/api/release';
import { $t } from '#/locales';

import { useSchema } from '../data';

import { breakpointsTailwind, useBreakpoints } from '@vueuse/core';

const emit = defineEmits(['success']);
const formData = ref<ReleaseApplicationApi.Application>();

const getTitle = computed(() => {
  return formData.value?.id
    ? $t('ui.actionTitle.edit', ['应用'])
    : $t('ui.actionTitle.create', ['应用']);
});

const breakpoints = useBreakpoints(breakpointsTailwind);
const isHorizontal = computed(() => breakpoints.greaterOrEqual('md').value);

const [Form, formApi] = useVbenForm({
  layout: 'vertical',
  schema: useSchema(),
  showDefaultActions: false,
});

function resetForm() {
  formApi.resetForm();
  formApi.setValues(formData.value || {});
}

const [Modal, modalApi] = useVbenModal({
  async onConfirm() {
    const { valid } = await formApi.validate();
    if (valid) {
      modalApi.lock();
      const data = await formApi.getValues();
      try {
        await (formData.value?.id
          ? updateApplication(formData.value.id, data)
          : createApplication(data));
        modalApi.close();
        emit('success');
      } finally {
        modalApi.lock(false);
      }
    }
  },
  onOpenChange(isOpen) {
    if (isOpen) {
      const data = modalApi.getData<ReleaseApplicationApi.Application>();
      if (data) {
        formData.value = data;
        // 确保 project 和 module 是 ID 而不是对象
        const projectId = typeof data.project === 'object' && data.project !== null ? (data.project as { id: number }).id : data.project;
        const moduleId = typeof data.module === 'object' && data.module !== null ? (data.module as { id: number }).id : data.module;
        const formValues = {
          ...data,
          project: projectId,
          module: moduleId,
        };
        formApi.setValues(formValues);
      } else {
        formData.value = undefined;
      }
    }
  },
});
</script>

<template>
  <Modal :title="getTitle">
    <Form class="mx-4" :layout="isHorizontal ? 'horizontal' : 'vertical'" />
    <template #prepend-footer>
      <div class="flex-auto">
        <Button type="primary" danger @click="resetForm">
          {{ $t('common.reset') }}
        </Button>
      </div>
    </template>
  </Modal>
</template>
