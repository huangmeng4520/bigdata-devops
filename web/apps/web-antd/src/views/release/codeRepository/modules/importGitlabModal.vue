<script lang="ts" setup>
import { ref, computed, onMounted } from 'vue';

import { Input, message, Pagination, Spin, Tag } from 'ant-design-vue';

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
const importedIds = ref<Set<number>>(new Set());

// 分页
const currentPage = ref(1);
const total = ref(0);
const pageSize = 50;

async function fetchProjects(page: number = 1) {
  loading.value = true;
  try {
    const result = await listGitLabProjects({
      search: searchText.value,
      page,
      per_page: pageSize,
    });
    console.log('[importGitlabModal] API response:', result);
    projects.value = result.projects || [];
    total.value = result.total || 0;
    importedIds.value = new Set(result.imported_ids || []);
    console.log('[importGitlabModal] projects count:', projects.value.length, 'total:', total.value, 'imported:', importedIds.value.size);
    selectedIds.value = [];
    currentPage.value = page;
  } catch (error) {
    console.error('[importGitlabModal] fetch error:', error);
    message.error('获取 GitLab Projects 失败');
    projects.value = [];
    total.value = 0;
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
  currentPage.value = 1;
  total.value = 0;
  importedIds.value = new Set();
}

function onSearch() {
  fetchProjects(1);
}

function onPageChange(page: number) {
  fetchProjects(page);
}

function isImported(projectId: number): boolean {
  return importedIds.value.has(projectId);
}

function toggleSelect(projectId: number) {
  if (isImported(projectId)) return;
  const idx = selectedIds.value.indexOf(projectId);
  if (idx >= 0) {
    selectedIds.value.splice(idx, 1);
  } else {
    selectedIds.value.push(projectId);
  }
}

// 未导入的项目列表
const importableProjects = computed(() => projects.value.filter(p => !isImported(p.id)));
const importableCount = computed(() => importableProjects.value.length);

function selectAll() {
  const allSelected = importableProjects.value.every(p => selectedIds.value.includes(p.id));
  if (allSelected) {
    // 取消全选
    selectedIds.value = [];
  } else {
    // 全选未导入的项目
    selectedIds.value = importableProjects.value.map(p => p.id);
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
        <Input.Search
          v-model:value="searchText"
          placeholder="搜索 GitLab Projects"
          enter-button="搜索"
          :loading="loading"
          @search="onSearch"
        />
      </div>

      <div class="info-bar">
        <label>
          <input 
            type="checkbox" 
            :checked="importableCount > 0 && selectedIds.length === importableCount"
            :disabled="importableCount === 0"
            @change="selectAll"
          />
          全选
        </label>
        <span>已选择 <Tag color="blue">{{ selectedIds.length }}</Tag> 个</span>
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
              :class="{ selected: selectedIds.includes(project.id), imported: isImported(project.id) }"
            >
              <label class="item-label" :class="{ disabled: isImported(project.id) }">
                <input 
                  type="checkbox" 
                  :checked="selectedIds.includes(project.id)"
                  :disabled="isImported(project.id)"
                  @change="toggleSelect(project.id)"
                />
                <div class="item-content">
                  <div class="item-name">
                    {{ project.name }}
                    <Tag v-if="isImported(project.id)" color="success" size="small">已导入</Tag>
                  </div>
                  <div class="item-path">{{ project.path_with_namespace }}</div>
                  <div v-if="project.description" class="item-desc">{{ project.description }}</div>
                </div>
              </label>
              <a :href="project.web_url" target="_blank" class="item-link">查看</a>
            </div>
          </template>
        </Spin>
      </div>

      <div v-if="total > pageSize" class="pagination-bar">
        <Pagination
          v-model:current="currentPage"
          :total="total"
          :page-size="pageSize"
          :show-size-changer="false"
          size="small"
          @change="onPageChange"
        />
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
.list-item.imported {
  background: #f9f9f9;
}
.item-label {
  display: flex;
  align-items: center;
  cursor: pointer;
  flex: 1;
}
.item-label.disabled {
  cursor: not-allowed;
  opacity: 0.7;
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
.pagination-bar {
  display: flex;
  justify-content: center;
  margin-top: 12px;
}
</style>
