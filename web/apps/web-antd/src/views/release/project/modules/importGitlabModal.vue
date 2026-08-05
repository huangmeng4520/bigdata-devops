<script lang="ts" setup>
import { ref } from 'vue';

import { message, Spin, Select, SelectOption, InputSearch } from 'ant-design-vue';

import { useVbenModal } from '@vben/common-ui';

import { listGitLabGroups, importGitLabGroups } from '#/api/release/project';

interface GitLabGroup {
  id: number;
  name: string;
  path: string;
  full_path: string;
  description: string;
  web_url: string;
}

const emit = defineEmits<{
  success: [];
}>();

const loading = ref(false);
const importing = ref(false);
const groups = ref<GitLabGroup[]>([]);
const selectedGroupIds = ref<number[]>([]);
const searchText = ref('');

async function fetchGroups() {
  loading.value = true;
  try {
    const data = await listGitLabGroups({ search: searchText.value, per_page: 50 });
    groups.value = data || [];
    selectedGroupIds.value = [];
  } catch (error) {
    message.error('获取 GitLab Groups 失败');
    groups.value = [];
  } finally {
    loading.value = false;
  }
}

function handleSearch() {
  fetchGroups();
}

async function handleConfirm() {
  if (selectedGroupIds.value.length === 0) {
    message.warning('请选择要导入的 Group');
    return;
  }

  importing.value = true;
  try {
    const result = await importGitLabGroups(selectedGroupIds.value);
    message.success(result.message || '导入成功');
    emit('success');
    selectedGroupIds.value = [];
    searchText.value = '';
    groups.value = [];
  } catch (error: any) {
    message.error(error?.message || '导入失败');
  } finally {
    importing.value = false;
  }
}

function toggleSelect(groupId: number) {
  const idx = selectedGroupIds.value.indexOf(groupId);
  if (idx >= 0) {
    selectedGroupIds.value.splice(idx, 1);
  } else {
    selectedGroupIds.value.push(groupId);
  }
}

function selectAll() {
  if (selectedGroupIds.value.length === groups.value.length) {
    selectedGroupIds.value = [];
  } else {
    selectedGroupIds.value = groups.value.map(g => g.id);
  }
}

const [Modal, modalApi] = useVbenModal({
  onConfirm: handleConfirm,
  onOpenChange: (isOpen: boolean) => {
    if (isOpen) {
      selectedGroupIds.value = [];
      searchText.value = '';
      groups.value = [];
      fetchGroups();
    }
  },
});
</script>

<template>
  <Modal 
    title="从 GitLab 批量导入 Groups" 
    :confirm-loading="importing" 
    :confirm-button-props="{ disabled: selectedGroupIds.length === 0 }"
    width="700px"
  >
    <div class="import-container">
      <div class="search-bar">
        <a-input-search
          v-model:value="searchText"
          placeholder="搜索 GitLab Groups"
          enter-button="搜索"
          :loading="loading"
          @search="handleSearch"
        />
      </div>

      <div class="info-bar">
        <label>
          <input 
            type="checkbox" 
            :checked="groups.length > 0 && selectedGroupIds.length === groups.length"
            :indeterminate="selectedGroupIds.length > 0 && selectedGroupIds.length < groups.length"
            @change="selectAll"
          />
          全选
        </label>
        <span>已选择 <a-tag color="blue">{{ selectedGroupIds.length }}</a-tag> 个</span>
      </div>

      <div class="list-box">
        <Spin :spinning="loading">
          <template v-if="groups.length === 0">
            <div class="empty-tip">暂无可导入的 Group</div>
          </template>
          <template v-else>
            <div 
              v-for="group in groups" 
              :key="group.id" 
              class="list-item"
              :class="{ selected: selectedGroupIds.includes(group.id) }"
            >
              <label class="item-label">
                <input 
                  type="checkbox" 
                  :checked="selectedGroupIds.includes(group.id)"
                  @change="toggleSelect(group.id)"
                />
                <div class="item-content">
                  <div class="item-name">{{ group.name }}</div>
                  <div class="item-path">{{ group.full_path }}</div>
                </div>
              </label>
              <a :href="group.web_url" target="_blank" class="item-link">查看</a>
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
.item-link {
  font-size: 12px;
}
</style>
