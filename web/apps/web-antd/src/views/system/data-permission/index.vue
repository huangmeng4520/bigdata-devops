<script lang="ts" setup>
import { computed, onMounted, ref } from 'vue';

import { Page } from '@vben/common-ui';
import { useDebounceFn } from '@vueuse/core';

import { message } from 'ant-design-vue';
import {
  Button as AButton,
  Card as ACard,
  Checkbox as ACheckbox,
  CheckboxGroup as ACheckboxGroup,
  Col as ACol,
  Empty as AEmpty,
  InputSearch as AInputSearch,
  Menu as AMenu,
  MenuItem as AMenuItem,
  Pagination as APagination,
  Row as ARow,
  Spin as ASpin,
  Tooltip as ATooltip,
} from 'ant-design-vue';

import { getProjectList } from '#/api/release';
import { getUserList } from '#/api/release/deployment';
import {
  assignDataPermission,
  getScopeUsers,
} from '#/api/system/dataPermissionRule';
import { hasPermission } from '#/utils/permission';

const canQuery = computed(() => hasPermission('system:data_permission_rule:query'));
const canEdit = computed(() => hasPermission('system:data_permission_rule:edit'));

interface ProjectItem {
  id: number;
  name: string;
  code: string;
}

// 项目列表（左侧，数据权限根节点）—— 后端分页 + 远程搜索
const PROJECT_PAGE_SIZE = 20;
const projects = ref<ProjectItem[]>([]);
const projectLoading = ref(false);
const selectedProjectId = ref<null | number>(null);
const projectKeyword = ref('');
const projectPage = ref(1);
const projectTotal = ref(0);

// 用户池（右侧研发）
const allUsers = ref<{ id: number; nickname: string; username: string }[]>([]);
const userLoading = ref(false);
const keyword = ref('');

// 已分配的研发 user_id
const assignedUserIds = ref<number[]>([]);
const saving = ref(false);

// 选中项目可能在其他分页，独立保存其展示信息，避免翻页后右侧标题丢失
const selectedProjectInfo = ref<null | ProjectItem>(null);
const selectedProject = computed(() => {
  if (selectedProjectId.value === null) return null;
  // 优先从当前页查找（保证名称/code 实时一致），否则回退到记录的信息
  return (
    projects.value.find((p) => p.id === selectedProjectId.value) ||
    selectedProjectInfo.value
  );
});

const filteredUsers = computed(() => {
  if (!keyword.value) return allUsers.value;
  const kw = keyword.value.toLowerCase();
  return allUsers.value.filter(
    (u) =>
      u.username.toLowerCase().includes(kw) ||
      (u.nickname || '').toLowerCase().includes(kw),
  );
});

async function loadProjects() {
  projectLoading.value = true;
  try {
    const params: Record<string, any> = {
      page: projectPage.value,
      pageSize: PROJECT_PAGE_SIZE,
      status: 1,
    };
    if (projectKeyword.value) {
      // ProjectFilter.name 为 icontains 模糊匹配
      params.name = projectKeyword.value;
    }
    const res = await getProjectList(params);
    const data = (res as any) || {};
    const list = data.items ?? data.data ?? [];
    projects.value = list;
    projectTotal.value = data.total ?? list.length ?? 0;
  } finally {
    projectLoading.value = false;
  }
}

// 远程搜索防抖：输入即查后端，避免一次性加载全部
const debouncedSearchProjects = useDebounceFn(() => {
  projectPage.value = 1;
  loadProjects();
}, 350);

function onProjectKeywordChange() {
  // v-model 已同步 projectKeyword，仅触发防抖搜索
  debouncedSearchProjects();
}

function onProjectPageChange(page: number) {
  projectPage.value = page;
  loadProjects();
}

async function loadUsers() {
  userLoading.value = true;
  try {
    const res = await getUserList({ page: 1, pageSize: 999 });
    allUsers.value = (res.items || []).map((u: any) => ({
      id: u.id,
      username: u.username,
      nickname: u.nickname,
    }));
  } finally {
    userLoading.value = false;
  }
}

async function loadScopeUsers(projectId: number) {
  const res = await getScopeUsers({
    scope_type: 'project',
    scope_id: projectId,
  });
  assignedUserIds.value = (res || []).map((r) => r.user_id);
}

async function onSelectProject(project: ProjectItem) {
  selectedProjectId.value = project.id;
  selectedProjectInfo.value = project;
  assignedUserIds.value = [];
  await loadScopeUsers(project.id);
}

async function onSave() {
  if (selectedProjectId.value === null) return;
  saving.value = true;
  try {
    const res = await assignDataPermission({
      scope_type: 'project',
      scope_id: selectedProjectId.value,
      user_ids: assignedUserIds.value,
    });
    message.success(`已保存，共分配 ${res.count} 名研发`);
  } catch {
    // 错误提示由全局拦截器处理
  } finally {
    saving.value = false;
  }
}

onMounted(async () => {
  if (!canQuery) return;
  // 并行加载首页项目 + 用户池；不再自动选中第一个项目（分页后让用户主动选择）
  await Promise.all([loadProjects(), loadUsers()]);
});
</script>

<template>
  <Page auto-content-height>
    <div
      v-if="!canQuery"
      class="flex h-full items-center justify-center text-gray-400"
    >
      无权访问「项目权限分配」
    </div>
    <div v-else class="flex h-full flex-col">
      <a-row :gutter="16" class="min-h-0 flex-1">
        <!-- 左：项目列表（数据权限根节点） -->
        <a-col :span="8" class="h-full">
          <a-card
            title="项目列表"
            :loading="projectLoading"
            class="h-full flex flex-col"
            :body-style="{ flex: '1', overflow: 'hidden', padding: '0' }"
          >
            <div class="border-b px-2 py-2">
              <a-input-search
                v-model:value="projectKeyword"
                placeholder="搜索项目名称"
                allow-clear
                size="small"
                @change="onProjectKeywordChange"
                @search="onProjectKeywordChange"
              />
            </div>
            <div class="flex-1 overflow-auto">
              <a-empty
                v-if="projects.length === 0"
                description="暂无项目"
                class="mt-10"
              />
              <a-menu
                v-else
                mode="inline"
                :selected-keys="
                  selectedProjectId !== null ? [String(selectedProjectId)] : []
                "
                class="border-0"
              >
                <a-menu-item
                  v-for="project in projects"
                  :key="String(project.id)"
                  @click="onSelectProject(project)"
                >
                  {{ project.name }}
                  <span class="ml-2 text-gray-400">{{ project.code }}</span>
                </a-menu-item>
              </a-menu>
            </div>
            <div class="border-t flex justify-end px-2 py-2">
              <a-pagination
                :current="projectPage"
                :page-size="PROJECT_PAGE_SIZE"
                :total="projectTotal"
                size="small"
                :show-size-changer="false"
                :show-total="(t: number) => `共 ${t} 个`"
                @change="onProjectPageChange"
              />
            </div>
          </a-card>
        </a-col>

        <!-- 右：研发分配 -->
        <a-col :span="16" class="h-full">
          <a-card
            :title="selectedProject ? `研发分配 - ${selectedProject.name}` : '研发分配'"
            class="h-full flex flex-col"
            :body-style="{ flex: '1', overflow: 'auto', padding: '16px' }"
          >
          <a-spin :spinning="userLoading">
            <div
              v-if="selectedProjectId === null"
              class="py-10 text-center text-gray-400"
            >
              请先在左侧选择一个项目
            </div>
            <template v-else>
              <div class="mb-3 flex items-center justify-between gap-3">
                <a-input-search
                  v-model:value="keyword"
                  placeholder="搜索用户名 / 昵称"
                  allow-clear
                  class="flex-1"
                />
                <a-tooltip
                  :title="canEdit ? '' : '当前账号无「项目权限分配-编辑」权限'"
                >
                  <a-button
                    type="primary"
                    :disabled="!canEdit || saving"
                    :loading="saving"
                    @click="onSave"
                  >
                    保存分配
                  </a-button>
                </a-tooltip>
              </div>
                <a-checkbox-group
                  v-model:value="assignedUserIds"
                  class="flex flex-wrap content-start gap-x-6 gap-y-2"
                >
                  <a-checkbox
                    v-for="u in filteredUsers"
                    :key="u.id"
                    :value="u.id"
                    class="!mr-0"
                  >
                    {{ u.nickname || u.username }}
                    <span class="ml-1 text-gray-400">{{ u.username }}</span>
                  </a-checkbox>
                </a-checkbox-group>
                <a-empty
                  v-if="filteredUsers.length === 0"
                  description="无匹配用户"
                  class="mt-6"
                />
            </template>
          </a-spin>
        </a-card>
      </a-col>
      </a-row>
    </div>
  </Page>
</template>
