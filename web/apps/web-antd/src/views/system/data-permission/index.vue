<script lang="ts" setup>
import type { ReleaseApplicationApi } from '#/api/release';

import { computed, onMounted, ref } from 'vue';

import { Page } from '@vben/common-ui';

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
import { hasPermission, op } from '#/utils/permission';

const canQuery = computed(() => hasPermission('system:data_permission_rule:query'));
const canEdit = computed(() => hasPermission('system:data_permission_rule:edit'));

interface ProjectItem {
  id: number;
  name: string;
  code: string;
}

// 项目列表（左侧，数据权限根节点）
const projects = ref<ProjectItem[]>([]);
const projectLoading = ref(false);
const selectedProjectId = ref<null | number>(null);

// 用户池（右侧研发）
const allUsers = ref<{ id: number; nickname: string; username: string }[]>([]);
const userLoading = ref(false);
const keyword = ref('');

// 已分配的研发 user_id
const assignedUserIds = ref<number[]>([]);
const saving = ref(false);

const selectedProject = computed(() =>
  projects.value.find((p) => p.id === selectedProjectId.value),
);

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
    const res = await getProjectList({
      page: 1,
      page_size: 999,
      status: 1,
    });
    // 兼容后端两种返回结构：{items} 或 {data}
    const list = (res as any).items ?? (res as any).data ?? [];
    projects.value = list;
  } finally {
    projectLoading.value = false;
  }
}

async function loadUsers() {
  userLoading.value = true;
  try {
    const res = await getUserList({ page: 1, page_size: 999 });
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

async function onSelectProject(projectId: number) {
  selectedProjectId.value = projectId;
  assignedUserIds.value = [];
  if (projectId !== null) {
    await loadScopeUsers(projectId);
  }
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
  await loadProjects();
  const tasks = [loadUsers()];
  if (projects.value.length) {
    tasks.push(onSelectProject(projects.value[0].id));
  }
  await Promise.all(tasks);
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
            :body-style="{ flex: '1', overflow: 'auto', padding: '8px 0' }"
          >
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
                @click="onSelectProject(project.id)"
              >
                {{ project.name }}
                <span class="ml-2 text-gray-400">{{ project.code }}</span>
              </a-menu-item>
            </a-menu>
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
