<script lang="ts" setup>
import { ref, onMounted } from 'vue';

import { message, Spin, Select } from 'ant-design-vue';

import { useVbenModal } from '@vben/common-ui';

import { listGitLabSubgroups, importGitLabSubgroups } from '#/api/release/module';
import { getProjectList } from '#/api/release/project';

interface GitLabSubgroup {
  id: number;
  name: string;
  path: string;
  full_path: string;
  description: string;
  web_url: string;
}

interface ProjectOption {
  id: number;
  name: string;
  code: string;
  gitlab_group_id: number;
}

const emit = defineEmits<{
  success: [];
}>();

const loading = ref(false);
const importing = ref(false);
const subgroups = ref<GitLabSubgroup[]>([]);
const selectedIds = ref<number[]>([]);
const parentGroupId = ref<number | undefined>(undefined);
const projectList = ref<ProjectOption[]>([]);
const selectedProject = ref<number | undefined>(undefined);

async function fetchProjects() {
  try {
    const data = await getProjectList({ page: 1, per_page: 100 });
    const list = Array.isArray(data) ? data : data?.items || [];
    projectList.value = list.filter(
      (p: ProjectOption) => p.gitlab_group_id && p.gitlab_group_id > 0
    );
  } catch (error) {
    console.error('获取项目列表失败', error);
  }
}

async function fetchSubgroups() {
  if (!selectedProject.value) {
    message.warning('请选择所属项目');
    return;
  }
  
  const project = projectList.value.find(p => p.id === selectedProject.value);
  if (!project?.gitlab_group_id) {
    message.warning('所选项目未关联 GitLab Group');
    return;
  }
  
  parentGroupId.value = project.gitlab_group_id;
  loading.value = true;
  try {
    const data = await listGitLabSubgroups({ 
      parent_id: parentGroupId.value, 
      per_page: 50 
    });
    subgroups.value = data || [];
    selectedIds.value = [];
  } catch (error) {
    console.error('获取 GitLab Subgroups 失败', error);
    message.error('获取 GitLab Subgroups 失败');
    subgroups.value = [];
  } finally {
    loading.value = false;
  }
}

async function handleConfirm() {
  if (selectedIds.value.length === 0) {
    message.warning('请选择要导入的 Subgroup');
    return;
  }

  if (!selectedProject.value) {
    message.warning('请选择所属项目');
    return;
  }

  importing.value = true;
  try {
    const data = selectedIds.value.map((id) => ({
      gitlab_subgroup_id: id,
      project_id: selectedProject.value,
    }));
    const result = await importGitLabSubgroups(data);
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
  parentGroupId.value = undefined;
  selectedProject.value = undefined;
  subgroups.value = [];
}

function toggleSelect(subgroupId: number) {
  const idx = selectedIds.value.indexOf(subgroupId);
  if (idx >= 0) {
    selectedIds.value.splice(idx, 1);
  } else {
    selectedIds.value.push(subgroupId);
  }
}

function selectAll() {
  if (selectedIds.value.length === subgroups.value.length) {
    selectedIds.value = [];
  } else {
    selectedIds.value = subgroups.value.map(s => s.id);
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
    }
  },
});
</script>

<template>
  <Modal 
    title="从 GitLab 批量导入 Subgroups" 
    :confirm-loading="importing" 
    :confirm-button-props="{ disabled: selectedIds.length === 0 }"
    width="700px"
  >
    <div class="import-container">
      <div class="filter-bar">
        <span>所属项目: </span>
        <Select
          v-model:value="selectedProject"
          placeholder="选择项目"
          style="width: 250px"
          :options="projectList.map(p => ({ value: p.id, label: `${p.name} (${p.code})` }))"
          :field-names="{ label: 'label', value: 'value' }"
          show-search
          :filter-option="(input: string, option: any) => option.label.toLowerCase().includes(input.toLowerCase())"
          @change="() => { subgroups = []; selectedIds = []; parentGroupId = undefined; }"
        />
        <a-button 
          type="primary" 
          :loading="loading" 
          :disabled="!selectedProject"
          @click="fetchSubgroups" 
          style="margin-left: 8px"
        >
          获取 Subgroups
        </a-button>
      </div>

      <div class="info-bar">
        <label>
          <input 
            type="checkbox" 
            :checked="subgroups.length > 0 && selectedIds.length === subgroups.length"
            @change="selectAll"
          />
          全选
        </label>
        <span>已选择 <a-tag color="blue">{{ selectedIds.length }}</a-tag> 个</span>
      </div>

      <div class="list-box">
        <Spin :spinning="loading">
          <template v-if="!selectedProject">
            <div class="empty-tip">请选择所属项目获取其 Subgroups</div>
          </template>
          <template v-else-if="subgroups.length === 0">
            <div class="empty-tip">暂无可导入的 Subgroup</div>
          </template>
          <template v-else>
            <div 
              v-for="subgroup in subgroups" 
              :key="subgroup.id" 
              class="list-item"
              :class="{ selected: selectedIds.includes(subgroup.id) }"
            >
              <label class="item-label">
                <input 
                  type="checkbox" 
                  :checked="selectedIds.includes(subgroup.id)"
                  @change="toggleSelect(subgroup.id)"
                />
                <div class="item-content">
                  <div class="item-name">{{ subgroup.name }}</div>
                  <div class="item-path">{{ subgroup.full_path }}</div>
                </div>
              </label>
              <a :href="subgroup.web_url" target="_blank" class="item-link">查看</a>
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
.filter-bar {
  display: flex;
  align-items: center;
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
