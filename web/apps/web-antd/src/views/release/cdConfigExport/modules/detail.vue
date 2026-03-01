<script lang="ts" setup>
import type { CDConfigExportApi } from '#/api/release';

import { ref, computed } from 'vue';

import { useVbenModal } from '@vben/common-ui';

import { Tag } from 'ant-design-vue';

const [Modal, modalApi] = useVbenModal({
  async onConfirm() {
    modalApi.close();
  },
  async onOpenChange(isOpen) {
    if (isOpen) {
      const data = modalApi.getData<CDConfigExportApi.Export>();
      currentExport.value = data ?? null;
    }
  },
});

const currentExport = ref<CDConfigExportApi.Export | null>(null);

const modalTitle = computed(() => {
  return currentExport.value ? `导出详情 - ${currentExport.value.application_name}` : '导出详情';
});

// 获取环境显示文本
function getEnvironmentText(env: string) {
  const envMap: Record<string, string> = {
    dev: '开发环境',
    test: '测试环境',
    staging: '准生产环境',
    production: '生产环境',
  };
  return envMap[env] || env;
}
</script>

<template>
  <Modal :title="modalTitle" class="w-[800px]">
    <div v-if="currentExport" class="space-y-4">
      <a-descriptions :column="2" bordered size="small">
        <a-descriptions-item label="应用名称">
          {{ currentExport.application_name }}
        </a-descriptions-item>
        <a-descriptions-item label="环境">
          <Tag color="blue">{{ getEnvironmentText(currentExport.environment) }}</Tag>
        </a-descriptions-item>
        <a-descriptions-item label="配置版本">
          v{{ currentExport.config_version }}
        </a-descriptions-item>
        <a-descriptions-item label="导出格式">
          <Tag color="green">{{ currentExport.export_format }}</Tag>
        </a-descriptions-item>
        <a-descriptions-item label="导出人">
          {{ currentExport.exported_by }}
        </a-descriptions-item>
        <a-descriptions-item label="下载次数">
          {{ currentExport.download_count }}
        </a-descriptions-item>
        <a-descriptions-item label="导出时间" :span="2">
          {{ currentExport.create_time }}
        </a-descriptions-item>
      </a-descriptions>

      <div>
        <div class="text-sm font-medium mb-2">导出内容：</div>
        <pre class="bg-gray-50 p-4 rounded text-sm overflow-auto max-h-96 font-mono">{{ currentExport.content }}</pre>
      </div>
    </div>
  </Modal>
</template>
