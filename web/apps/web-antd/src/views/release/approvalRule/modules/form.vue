<script lang="ts" setup>
import type { ApprovalRuleApi } from '#/api/release';

import { computed, ref, watch } from 'vue';

import { useVbenModal } from '@vben/common-ui';

import {
  Form,
  FormItem,
  Input,
  InputNumber,
  message,
  Radio,
  RadioGroup,
  Select,
  SelectOption,
  Switch,
} from 'ant-design-vue';

import {
  createApprovalRule,
  getApprovalRuleDetail,
  getApplicationList,
  getProjectList,
  getUserList,
  NOTIFY_CHANNEL_OPTIONS,
  RULE_TYPE_OPTIONS,
  TIMEOUT_ACTION_OPTIONS,
  updateApprovalRule,
} from '#/api/release';
import { ENVIRONMENT_OPTIONS } from '#/api/release/record';

const emit = defineEmits(['success']);

const [Modal, modalApi] = useVbenModal({
  async onConfirm() {
    await handleSubmit();
  },
  async onOpenChange(isOpen) {
    if (isOpen) {
      const data = modalApi.getData<ApprovalRuleApi.ApprovalRule>();
      if (data?.id) {
        await loadData(data.id);
      } else {
        resetForm();
      }
      // 打开时加载项目列表
      loadProjectOptions();
    }
  },
});

// 表单数据
const formData = ref<Partial<ApprovalRuleApi.ApprovalRule> & { scope?: string }>({
  name: '',
  code: '',
  scope: 'global',
  project: null,
  application: null,
  environment: 'production',
  rule_type: 'single',
  approvers: [],
  min_approvers: 1,
  timeout_hours: 24,
  timeout_action: 'reject',
  notify_channels: ['site'],
  is_default: false,
  status: 1,
});

// 选中的审批人用户 id 列表（用于多选 Select 的 v-model）
const selectedUserIds = ref<number[]>([]);
// 用户选项
const userOptions = ref<
  Array<{ id: number; username: string; nickname?: string; email?: string }>
>([]);
const userSearchLoading = ref(false);

// 项目 / 应用选项
const projectOptions = ref<Array<{ label: string; value: number }>>([]);
const applicationOptions = ref<Array<{ label: string; value: number }>>([]);
const appLoading = ref(false);

const isEdit = computed(() => !!formData.value.id);
const modalTitle = computed(() => (isEdit.value ? '编辑审批规则' : '创建审批规则'));

// 作用域：项目/应用字段是否显示
const showProject = computed(
  () => formData.value.scope === 'project' || formData.value.scope === 'application',
);
const showApplication = computed(
  () => formData.value.scope === 'application',
);
// min_approvers 仅 any 类型显示
const showMinApprovers = computed(() => formData.value.rule_type === 'any');

// 作用域变化时清理 project/application
watch(
  () => formData.value.scope,
  (scope) => {
    if (scope === 'global') {
      formData.value.project = null;
      formData.value.application = null;
    } else if (scope === 'project') {
      formData.value.application = null;
    }
  },
);

// 项目变化时重新加载应用列表
watch(
  () => formData.value.project,
  (projectId) => {
    if (projectId) {
      loadApplicationOptions(projectId);
    } else {
      applicationOptions.value = [];
    }
    // 清空已选应用
    if (formData.value.application) {
      formData.value.application = null;
    }
  },
);

// 加载项目列表
async function loadProjectOptions() {
  try {
    const res = await getProjectList({ page: 1, pageSize: 200 });
    projectOptions.value = (res.items || []).map((p) => ({
      label: p.name,
      value: p.id,
    }));
  } catch {
    projectOptions.value = [];
  }
}

// 加载应用列表（按项目过滤）
async function loadApplicationOptions(projectId: number) {
  appLoading.value = true;
  try {
    const res = await getApplicationList({ project: projectId, page: 1, pageSize: 200 });
    applicationOptions.value = (res.items || []).map((a) => ({
      label: a.name,
      value: a.id,
    }));
  } catch {
    applicationOptions.value = [];
  } finally {
    appLoading.value = false;
  }
}

// 搜索用户（使用后端 SearchFilter 支持用户名/昵称/手机号多字段搜索）
async function handleUserSearch(value: string) {
  if (!value || value.length < 1) return;
  userSearchLoading.value = true;
  try {
    const res = await getUserList({ search: value, page: 1, pageSize: 20 });
    const list = (res?.items || []).map((user: any) => ({
      id: user.id,
      username: user.username,
      nickname: user.nickname || user.username,
      email: user.email || '',
    }));
    // 合并到已存在选项（避免重复）
    const existing = new Set(userOptions.value.map((u) => u.id));
    list.forEach((u: { id: number; username: string; nickname?: string; email?: string }) => {
      if (!existing.has(u.id)) userOptions.value.push(u);
    });
  } catch (error) {
    console.error('搜索用户失败:', error);
  } finally {
    userSearchLoading.value = false;
  }
}

// 重置表单
function resetForm() {
  formData.value = {
    name: '',
    code: '',
    scope: 'global',
    project: null,
    application: null,
    environment: 'production',
    rule_type: 'single',
    approvers: [],
    min_approvers: 1,
    timeout_hours: 24,
    timeout_action: 'reject',
    notify_channels: ['site'],
    is_default: false,
    status: 1,
  };
  selectedUserIds.value = [];
  userOptions.value = [];
  applicationOptions.value = [];
}

// 加载编辑数据
async function loadData(id: number) {
  try {
    const result = await getApprovalRuleDetail(id);
    formData.value = { ...result };
    // 推断作用域（后端已返回 scope 字段，直接使用）
    formData.value.scope = result.scope || 'global';
    // 回填审批人选项与已选 id
    selectedUserIds.value = (result.approvers || []).map((a) => a.user_id);
    userOptions.value = (result.approvers || []).map((a) => ({
      id: a.user_id,
      username: a.username,
      nickname: a.username,
      email: '',
    }));
    // 若有项目，加载应用列表以便回显
    if (result.project) {
      loadApplicationOptions(result.project);
    }
  } catch {
    message.error('加载数据失败');
  }
}

// 提交表单
async function handleSubmit() {
  // 校验
  if (!formData.value.name) {
    message.warning('请输入规则名称');
    throw new Error('请输入规则名称');
  }
  if (!formData.value.code) {
    message.warning('请输入规则编码');
    throw new Error('请输入规则编码');
  }
  if (showProject.value && !formData.value.project) {
    message.warning('请选择项目');
    throw new Error('请选择项目');
  }
  if (showApplication.value && !formData.value.application) {
    message.warning('请选择应用');
    throw new Error('请选择应用');
  }
  if (showMinApprovers.value && (!formData.value.min_approvers || formData.value.min_approvers < 1)) {
    message.warning('请填写最少通过人数');
    throw new Error('请填写最少通过人数');
  }
  if (selectedUserIds.value.length === 0) {
    message.warning('请选择审批人');
    throw new Error('请选择审批人');
  }

  // 构造 approvers 数组：根据选中 id 与选项映射出 {user_id, username, order}
  const isSequential = formData.value.rule_type === 'sequential';
  const approvers = selectedUserIds.value.map((uid, idx) => {
    const user = userOptions.value.find((u) => u.id === uid);
    return {
      user_id: uid,
      username: user?.username || user?.nickname || String(uid),
      order: isSequential ? idx + 1 : idx + 1,
    };
  });

  // 组装提交数据
  const submitData: Partial<ApprovalRuleApi.ApprovalRule> = {
    name: formData.value.name,
    code: formData.value.code,
    // global 作用域下 project/application 传 null
    project: showProject.value ? formData.value.project : null,
    application: showApplication.value ? formData.value.application : null,
    environment: formData.value.environment,
    rule_type: formData.value.rule_type,
    approvers,
    min_approvers: formData.value.min_approvers || 1,
    timeout_hours: formData.value.timeout_hours || 24,
    timeout_action: formData.value.timeout_action,
    notify_channels: formData.value.notify_channels || [],
    is_default: !!formData.value.is_default,
    status: formData.value.status,
  };

  try {
    if (isEdit.value) {
      await updateApprovalRule(formData.value.id!, submitData);
      message.success('更新成功');
    } else {
      await createApprovalRule(submitData);
      message.success('创建成功');
    }
    modalApi.close();
    emit('success');
  } catch (error: any) {
    message.error(error?.message || '操作失败');
    throw error;
  }
}

// 作用域选项
const scopeOptions = [
  { label: '全局', value: 'global' },
  { label: '项目级', value: 'project' },
  { label: '应用级', value: 'application' },
];

// 状态选项
const statusOptions = [
  { label: '启用', value: 1 },
  { label: '禁用', value: 0 },
];
</script>

<template>
  <Modal :title="modalTitle" width="640px">
    <Form
      :model="formData"
      :label-col="{ span: 5 }"
      :wrapper-col="{ span: 18 }"
    >
      <!-- 规则名称 -->
      <FormItem
        label="规则名称"
        name="name"
        :rules="[{ required: true, message: '请输入规则名称' }]"
      >
        <Input v-model:value="formData.name" placeholder="请输入规则名称" />
      </FormItem>

      <!-- 规则编码 -->
      <FormItem
        label="规则编码"
        name="code"
        :rules="[{ required: true, message: '请输入规则编码' }]"
      >
        <Input
          v-model:value="formData.code"
          placeholder="如: prod-release-approval"
          :disabled="isEdit"
        />
      </FormItem>

      <!-- 作用域 -->
      <FormItem label="作用域" name="scope">
        <RadioGroup v-model:value="formData.scope">
          <Radio
            v-for="opt in scopeOptions"
            :key="opt.value"
            :value="opt.value"
          >
            {{ opt.label }}
          </Radio>
        </RadioGroup>
      </FormItem>

      <!-- 项目（scope=project/application 时显示） -->
      <FormItem
        v-if="showProject"
        label="项目"
        name="project"
        :rules="[{ required: true, message: '请选择项目' }]"
      >
        <Select
          v-model:value="formData.project"
          :options="projectOptions"
          placeholder="请选择项目"
          show-search
          option-filter-prop="label"
          allow-clear
        />
      </FormItem>

      <!-- 应用（scope=application 时显示） -->
      <FormItem
        v-if="showApplication"
        label="应用"
        name="application"
        :rules="[{ required: true, message: '请选择应用' }]"
      >
        <Select
          v-model:value="formData.application"
          :options="applicationOptions"
          :loading="appLoading"
          placeholder="请选择应用"
          show-search
          option-filter-prop="label"
          allow-clear
        />
      </FormItem>

      <!-- 环境 -->
      <FormItem
        label="环境"
        name="environment"
        :rules="[{ required: true, message: '请选择环境' }]"
      >
        <Select
          v-model:value="formData.environment"
          :options="ENVIRONMENT_OPTIONS"
          placeholder="请选择环境"
        />
      </FormItem>

      <!-- 规则类型 -->
      <FormItem
        label="规则类型"
        name="rule_type"
        :rules="[{ required: true, message: '请选择规则类型' }]"
      >
        <Select
          v-model:value="formData.rule_type"
          :options="RULE_TYPE_OPTIONS"
          placeholder="请选择规则类型"
        />
        <div v-if="formData.rule_type === 'sequential'" class="form-tip">
          顺序审批：审批人按顺序依次审批，可在审批人列表中查看顺序
        </div>
      </FormItem>

      <!-- 审批人 -->
      <FormItem
        label="审批人"
        name="approvers"
        :rules="[{ required: true, message: '请选择审批人' }]"
      >
        <Select
          v-model:value="selectedUserIds"
          mode="multiple"
          placeholder="输入用户名搜索并选择审批人"
          :filter-option="false"
          :loading="userSearchLoading"
          @search="handleUserSearch"
        >
          <SelectOption
            v-for="user in userOptions"
            :key="user.id"
            :value="user.id"
            :label="user.nickname || user.username"
          >
            <div class="user-option">
              <span class="username">{{ user.nickname || user.username }}</span>
              <span v-if="user.email" class="email">{{ user.email }}</span>
            </div>
          </SelectOption>
        </Select>
        <div class="form-tip">
          已选择 {{ selectedUserIds.length }} 位审批人
        </div>
      </FormItem>

      <!-- 最少通过人数（rule_type=any 时显示） -->
      <FormItem
        v-if="showMinApprovers"
        label="最少通过人数"
        name="min_approvers"
        :rules="[{ required: true, message: '请填写最少通过人数' }]"
      >
        <InputNumber
          v-model:value="formData.min_approvers"
          :min="1"
          :max="selectedUserIds.length || 99"
          style="width: 100%"
        />
      </FormItem>

      <!-- 超时小时数 -->
      <FormItem label="超时(小时)" name="timeout_hours">
        <InputNumber
          v-model:value="formData.timeout_hours"
          :min="1"
          :max="720"
          style="width: 100%"
        />
      </FormItem>

      <!-- 超时策略 -->
      <FormItem label="超时策略" name="timeout_action">
        <Select
          v-model:value="formData.timeout_action"
          :options="TIMEOUT_ACTION_OPTIONS"
          placeholder="请选择超时策略"
        />
      </FormItem>

      <!-- 通知渠道 -->
      <FormItem label="通知渠道" name="notify_channels">
        <Select
          v-model:value="formData.notify_channels"
          mode="multiple"
          :options="NOTIFY_CHANNEL_OPTIONS"
          placeholder="请选择通知渠道"
        />
      </FormItem>

      <!-- 是否默认 -->
      <FormItem label="默认规则" name="is_default">
        <Switch v-model:checked="formData.is_default" />
      </FormItem>

      <!-- 状态 -->
      <FormItem label="状态" name="status">
        <Select
          v-model:value="formData.status"
          :options="statusOptions"
          placeholder="请选择状态"
        />
      </FormItem>
    </Form>
  </Modal>
</template>

<style scoped>
.form-tip {
  margin-top: 4px;
  color: #999;
  font-size: 12px;
}

.user-option {
  display: flex;
  justify-content: space-between;
}

.user-option .username {
  font-weight: 500;
}

.user-option .email {
  color: #999;
  font-size: 12px;
}
</style>
