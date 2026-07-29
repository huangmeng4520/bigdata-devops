<script lang="ts" setup>
import { ref, onMounted } from 'vue';

import { message, Spin } from 'ant-design-vue';

import { useVbenModal } from '@vben/common-ui';

import { listGitLabProjects, importGitLabProjects } from '#/api/release/codeRepository';

interface GitLabProject {
  id: number;
  name: string;
  path: string;
  path_with_namespace: string;
  description: string;
  web_url: string;
}

const emit = defineEmits<{
  success: [];
}>();

const loading = ref(false);
const importing = ref(false);
const projects = ref<GitLabProject[]>([]);
const selectedIds = ref<number[]>([]);
const searchText = ref('');

async function fetchProjects() {
  loading.value = true;
  try {
    const data = await listGitLabProjects({ 
      search: searchText.value, 
      per_page: 50 
    });
    projects.value = data || [];
    selectedIds.value = [];
  } catch (error) {
    message.error('获取 GitLab Projects 失败');
    projects.value = [];
  } finally {
    loading.value = false;
  }
}

async function handleConfirm() {
  if (selectedIds.value.length === 0) {
    message.warning('请选择要导入的 Project');
    return;
  }

  importing.value = true;
  try {
    const data = selectedIds.value.map(id => ({
      gitlab_project_id: id
    }));
    const result = await importGitLabProjects(data);
    message.success(result.message || '导入成功');
    emit('success');
    resetForm();
  } catch (error: any) {
    message.error(error?.message || '导入失败');
  } finally {
    importing.value = false;
  }
}

function resetForm() {
  selectedIds.value = [];
  searchText.value = '';
  projects.value = [];
}

function toggleSelect(projectId: number) {
  const idx = selectedIds.value.indexOf(projectId);
  if (idx >= 0) {
    selectedIds.value.splice(idx, 1);
  } else {
    selectedIds.value.push(projectId);
  }
}

function selectAll() {
  if (selectedIds.value.length === projects.value.length) {
    selectedIds.value = [];
  } else {
    selectedIds.value = projects.value.map(p => p.id);
  }
}

onMounted(() => {
  fetchProjects();
});

const [Modal, modalApi] = useVbenModal({
  onConfirm: handleConfirm,
  onOpenChange: (isOpen: boolean) => {
    if (isOpen) {
      resetForm();
      fetchProjects();
    }
  },
});
</script>

<template>
  <Modal 
    title="从 GitLab 批量导入仓库" 
    :confirm-loading="importing" 
    :confirm-button-props="{ disabled: selectedIds.length === 0 }"
    width="800px"
  >
    <div class="import-container">
      <div class="search-bar">
        <a-input-search
          v-model:value="searchText"
          placeholder="搜索 GitLab Projects"
          enter-button="搜索"
          :loading="loading"
          @search="fetchProjects"
        />
      </div>

      <div class="info-bar">
        <label>
          <input 
            type="checkbox" 
            :checked="projects.length > 0 && selectedIds.length === projects.length"
            @change="selectAll"
          />
          全选
        </label>
        <span>已选择 <a-tag color="blue">{{ selectedIds.length }}</a-tag> 个</span>
      </div>

      <div class="list-box">
        <Spin :spinning="loading">
          <template v-if="projects.length === 0">
            <div class="empty-tip">暂无可导入的 Project</div>
          </template>
          <template v-else>
            <div 
              v-for="project in projects" 
              :key="project.id" 
              class="list-item"
              :class="{ selected: selectedIds.includes(project.id) }"
            >
              <label class="item-label">
                <input 
                  type="checkbox" 
                  :checked="selectedIds.includes(project.id)"
                  @change="toggleSelect(project.id)"
                />
                <div class="item-content">
                  <div class="item-name">{{ project.name }}</div>
                  <div class="item-path">{{ project.path_with_namespace }}</div>
                  <div v-if="project.description" class="item-desc">{{ project.description }}</div>
                </div>
              </label>
              <a :href="project.web_url" target="_blank" class="item-link">查看</a>
            </div>
          </template>
        </Spin>
      </div>
    </div>
  </Modal>
</template>

<style scoped>
.import-container {
  max-height: 500px;
}
.search-bar {
  margin-bottom: 12px;
}
.info-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding: 8px 12px;
  background: #f5f5f5;
  border-radius: 4px;
}
.info-bar label {
  cursor: pointer;
}
.list-box {
  max-height: 350px;
  overflow-y: auto;
  border: 1px solid #e8e8e8;
  border-radius: 4px;
}
.empty-tip {
  text-align: center;
  color: #999;
  padding: 40px;
}
.list-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  border-bottom: 1px solid #f0f0f0;
}
.list-item:last-child {
  border-bottom: none;
}
.list-item:hover {
  background: #fafafa;
}
.list-item.selected {
  background: #e6f7ff;
}
.item-label {
  display: flex;
  align-items: center;
  cursor: pointer;
  flex: 1;
}
.item-label input[type="checkbox"] {
  margin-right: 10px;
}
.item-content {
  flex: 1;
}
.item-name {
  font-weight: 500;
  font-size: 14px;
}
.item-path {
  color: #666;
  font-size: 12px;
  margin-top: 2px;
}
.item-desc {
  color: #999;
  font-size: 12px;
  margin-top: 2px;
}
.item-link {
  font-size: 12px;
}
</style>
