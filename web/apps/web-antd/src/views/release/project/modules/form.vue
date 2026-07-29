<script lang="ts" setup>
import type { ReleaseProjectApi } from '#/api/release';

import { computed, ref } from 'vue';

import { useVbenModal } from '@vben/common-ui';

import { Button } from 'ant-design-vue';

import { useVbenForm } from '#/adapter/form';
import { createProject, updateProject } from '#/api/release';
import { $t } from '#/locales';

import { useSchema } from '../data';

import { breakpointsTailwind, useBreakpoints } from '@vueuse/core';

const emit = defineEmits(['success']);
const formData = ref<ReleaseProjectApi.Project>();

const getTitle = computed(() => {
  return formData.value?.id
    ? $t('ui.actionTitle.edit', ['项目'])
    : $t('ui.actionTitle.create', ['项目']);
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
          ? updateProject(formData.value.id, data)
          : createProject(data));
        modalApi.close();
        emit('success');
      } finally {
        modalApi.lock(false);
      }
    }
  },
  onOpenChange(isOpen) {
    if (isOpen) {
      const data = modalApi.getData<ReleaseProjectApi.Project>();
      if (data) {
        formData.value = data;
        formApi.setValues(formData.value);
        if (data.id) {
          formApi.updateSchema([
            { fieldName: 'code', componentProps: { disabled: true } },
            { fieldName: 'gitlab_group_id', componentProps: { disabled: true } },
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
