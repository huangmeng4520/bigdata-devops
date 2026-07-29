<script lang="ts" setup>
import type { CodeRepositoryApi } from '#/api/release/codeRepository';

import { computed, ref } from 'vue';

import { useVbenModal } from '@vben/common-ui';

import { Button } from 'ant-design-vue';

import { useVbenForm } from '#/adapter/form';
import { createCodeRepository, updateCodeRepository } from '#/api/release/codeRepository';
import { $t } from '#/locales';

import { useFormSchema as useSchema } from '../data';

const emit = defineEmits<{
  success: [];
}>();

const formData = ref<CodeRepositoryApi.CodeRepository>();

const getTitle = computed(() => {
  return formData.value?.id
    ? $t('ui.actionTitle.edit', ['代码仓库'])
    : $t('ui.actionTitle.create', ['代码仓库']);
});

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
  onConfirm: async () => {
    const { valid } = await formApi.validate();
    if (valid) {
      modalApi.lock();
      const data = await formApi.getValues();
      try {
        await (formData.value?.id
          ? updateCodeRepository(formData.value.id, data)
          : createCodeRepository(data));
        modalApi.close();
        emit('success');
      } finally {
        modalApi.lock(false);
      }
    }
  },
  onOpenChange(isOpen: boolean) {
    if (isOpen) {
      const data = modalApi.getData<CodeRepositoryApi.CodeRepository>();
      if (data) {
        formData.value = data;
        // 确保 project 和 module 是 ID 而不是对象
        const projectId = typeof data.project === 'object' && data.project !== null 
          ? (data.project as { id: number }).id 
          : data.project;
        const moduleId = typeof data.module === 'object' && data.module !== null 
          ? (data.module as { id: number }).id 
          : data.module;
        const formValues = {
          ...data,
          project: projectId,
          module: moduleId,
        };
        formApi.setValues(formValues);
        if (data.id) {
          formApi.updateSchema([
            { fieldName: 'code', componentProps: { disabled: true } },
            { fieldName: 'project', componentProps: { disabled: true } },
            { fieldName: 'module', componentProps: { disabled: true } },
            { fieldName: 'default_branch', componentProps: { disabled: true } },
            { fieldName: 'repository_type', componentProps: { disabled: true } },
          ]);
        }
      } else {
        formData.value = undefined;
      }
    }
  },
});

defineExpose({
  open: modalApi.open,
});
</script>

<template>
  <Modal :title="getTitle">
    <Form />
  </Modal>
</template>
