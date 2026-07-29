<script lang="ts" setup>
import type { ReleaseModuleApi } from '#/api/release';

import { computed, ref } from 'vue';

import { useVbenModal } from '@vben/common-ui';

import { Button } from 'ant-design-vue';

import { useVbenForm } from '#/adapter/form';
import { createModule, updateModule } from '#/api/release';
import { $t } from '#/locales';

import { useSchema } from '../data';

import { breakpointsTailwind, useBreakpoints } from '@vueuse/core';

const emit = defineEmits(['success']);
const formData = ref<ReleaseModuleApi.Module>();

const getTitle = computed(() => {
  return formData.value?.id
    ? $t('ui.actionTitle.edit', ['模块'])
    : $t('ui.actionTitle.create', ['模块']);
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
          ? updateModule(formData.value.id, data)
          : createModule(data));
        modalApi.close();
        emit('success');
      } finally {
        modalApi.lock(false);
      }
    }
  },
  onOpenChange(isOpen) {
    if (isOpen) {
      const data = modalApi.getData<ReleaseModuleApi.Module>();
      if (data) {
        formData.value = data;
        // 确保 project 是 ID 而不是对象
        const projectId = typeof data.project === 'object' && data.project !== null ? (data.project as { id: number }).id : data.project;
        const formValues = {
          ...data,
          project: projectId,
        };
        formApi.setValues(formValues);
        if (data.id) {
          formApi.updateSchema([
            { fieldName: 'project', componentProps: { disabled: true } },
            { fieldName: 'name', componentProps: { disabled: true } },
            { fieldName: 'code', componentProps: { disabled: true } },
            { fieldName: 'gitlab_subgroup_id', componentProps: { disabled: true } },
          ]);
        } else if (formValues.project) {
          // 从项目/应用页跳转创建时预填了项目，禁用项目字段防止越权改选项目
          formApi.updateSchema([
            { fieldName: 'project', componentProps: { disabled: true } },
          ]);
        }
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
