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
  handleValuesChange(_values, fieldsChanged) {
    const changing = new Set(fieldsChanged);
    // project 变化 → 清空 module 与 code_repository，触发重新拉取
    if (changing.has('project')) {
      formApi.setFieldValue('code_repository', undefined);
      if (!changing.has('module')) {
        formApi.setFieldValue('module', undefined);
      }
    }
    // module 变化 → 清空 code_repository，使其按模块精确过滤
    if (changing.has('module') && !changing.has('project')) {
      formApi.setFieldValue('code_repository', undefined);
    }
  },
});

function resetForm() {
  const data = formData.value;
  if (!data) return;
  formApi.resetForm();
  const toId = (val: any) =>
    typeof val === 'object' && val !== null ? (val as { id: number }).id : val;
  formApi.setValues({
    ...data,
    project: toId(data.project),
    module: toId(data.module),
    code_repository: toId(data.code_repository),
  });
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
        const toId = (val: any) =>
          typeof val === 'object' && val !== null ? (val as { id: number }).id : val;
        formApi.setValues({
          ...data,
          project: toId(data.project),
          module: toId(data.module),
          code_repository: toId(data.code_repository),
        });
        if (data.id) {
          formApi.updateSchema([
            { fieldName: 'project', componentProps: { disabled: true } },
            { fieldName: 'module', componentProps: { disabled: true } },
            { fieldName: 'code_repository', componentProps: { disabled: true } },
            { fieldName: 'code', componentProps: { disabled: true } },
            { fieldName: 'git_url', componentProps: { disabled: true } },
          ]);
        }
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
