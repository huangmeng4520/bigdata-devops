<script lang="ts" setup>
import type { ReleaseApplicationApi } from '#/api/release';

import { computed, ref, watch } from 'vue';

import { useVbenModal } from '@vben/common-ui';

import { message, Spin, Tag, Input, Select, SelectOption, Textarea } from 'ant-design-vue';

import {
  type Environment,
  type ApprovalRule,
  type ReleaseParams,
  type UserOption,
  getAppEnvironments,
  getApprovalRules,
  getUserList,
  triggerRelease,
} from '#/api/release';

import { useRouter } from 'vue-router';

const emit = defineEmits<{
  success: [];
}>();

const router = useRouter();

const [Modal, modalApi] = useVbenModal({
  onConfirm: handleConfirm,
  onOpenChange: (isOpen: boolean) => {
    if (isOpen) {
      const data = modalApi.getData<ReleaseApplicationApi.Application>();
      console.log('ReleaseModal onOpenChange:', data);
      if (data) {
        application.value = data;
        resetForm();
        loadData();
      }
    }
  },
});

// 当前应用
const application = ref<ReleaseApplicationApi.Application | null>(null);

// 加载状态
const loading = ref(false);
const submitting = ref(false);

// 环境列表
const environments = ref<Environment[]>([]);
// 审批规则
const approvalRules = ref<ApprovalRule[]>([]);
// 用户列表（审批人）
const userOptions = ref<UserOption[]>([]);
// 用户搜索状态
const userSearchLoading = ref(false);

// 表单数据
const formData = ref<ReleaseParams>({
  branch: '',
  environment: '',
  version: '',
  require_approval: false,
  approval_type: '',
  approvers: [],
  remark: '',
});

// 选中的环境信息
const selectedEnv = computed(() => {
  return environments.value.find((e) => e.code === formData.value.environment);
});

// 监听环境变化，自动设置是否需要审批
watch(
  () => formData.value.environment,
  (env) => {
    if (env) {
      const envInfo = environments.value.find((e) => e.code === env);
      if (envInfo?.requires_approval) {
        formData.value.require_approval = true;
        // 加载该环境的审批规则
        loadApprovalRules(env);
      } else {
        formData.value.require_approval = false;
      }
    }
  },
);

// 加载数据
async function loadData() {
  if (!application.value) return;

  loading.value = true;
  try {
    // 加载环境配置
    // requestClient 已配置 defaultResponseInterceptor，自动解包返回 data 字段
    // 后端返回 {code: 0, data: [...]} -> 前端直接得到 [...]
    const envsRes = await getAppEnvironments(application.value.id).catch(() => []);
    environments.value = Array.isArray(envsRes) ? envsRes : [];

    if (environments.value.length === 0) {
      environments.value = [
        { code: 'dev', name: '开发环境', has_pipeline_config: false, requires_approval: false },
        { code: 'test', name: '测试环境', has_pipeline_config: false, requires_approval: false },
        { code: 'staging', name: '准生产环境', has_pipeline_config: false, requires_approval: true },
        { code: 'production', name: '生产环境', has_pipeline_config: false, requires_approval: true },
      ];
    }

    // 设置默认分支
    formData.value.branch = application.value.build_branch || 'main';
  } catch (error) {
    message.error('加载数据失败');
    console.error(error);
  } finally {
    loading.value = false;
  }
}

// 加载审批规则
async function loadApprovalRules(environment: string) {
  try {
    const res = await getApprovalRules({ environment });
    approvalRules.value = res || [];
    
    // 如果有默认规则，自动选择
    if (approvalRules.value.length > 0) {
      formData.value.approval_type = approvalRules.value[0].code;
      // 预设审批人
      if (approvalRules.value[0].approvers?.length > 0) {
        formData.value.approvers = approvalRules.value[0].approvers.map((a: any) => ({
          id: a.id,
          name: a.name,
        }));
      }
    }
  } catch (error) {
    console.error('加载审批规则失败', error);
  }
}

// 搜索用户
async function handleUserSearch(value: string) {
  if (!value || value.length < 1) {
    return;
  }
  
  userSearchLoading.value = true;
  try {
    const res = await getUserList({ username: value, page_size: 20 });
    userOptions.value = (res.results || []).map((user: any) => ({
      id: user.id,
      username: user.username,
      nickname: user.nickname || user.username,
      email: user.email || '',
    }));
  } catch (error) {
    console.error('搜索用户失败', error);
  } finally {
    userSearchLoading.value = false;
  }
}

// 确认发布
async function handleConfirm() {
  if (!application.value) return false;

  // 验证
  if (!formData.value.branch) {
    message.warning('请选择发布分支');
    return false;
  }
  if (!formData.value.environment) {
    message.warning('请选择目标环境');
    return false;
  }
  if (formData.value.require_approval && formData.value.approvers.length === 0) {
    message.warning('请选择审批人');
    return false;
  }

  submitting.value = true;
  try {
    // 构建提交数据
    const submitData: any = {
      branch: formData.value.branch,
      environment: formData.value.environment,
      require_approval: formData.value.require_approval,
      approvers: formData.value.approvers,
      remark: formData.value.remark || '',
    };
    // 版本号：始终传递，即使为空
  if (formData.value.version) {
    submitData.version = formData.value.version;
  }
    // 审批类型
    if (formData.value.approval_type) {
      submitData.approval_type = formData.value.approval_type;
    }

    console.log('提交发布数据:', submitData);
    const res: any = await triggerRelease(application.value.id, submitData);

    // 根据返回状态判断是否关闭对话框并跳转
    const successStatuses = ['building', 'pending', 'approval_pending'];
    if (successStatuses.includes(res.status)) {
      message.success(res.message);

      // 重置表单
      resetForm();

      // 关闭弹窗
      modalApi.close();
      emit('success');

      // 跳转到发布记录页面
      router.push('/release/record');
    } else if (res.status === 'build_failed') {
      // 构建触发失败，不关闭弹窗，显示错误
      message.error(res.message || '触发构建失败');
    } else {
      // 其他情况
      message.warning(res.message || '发布已创建');
    }

    return true;
  } catch (error: any) {
    console.error('发布失败:', error);
    message.error(error?.message || error?.response?.data?.error || '发布失败');
    return false;
  } finally {
    submitting.value = false;
  }
}

// 重置表单
function resetForm() {
  formData.value = {
    branch: '',
    environment: '',
    version: '',
    require_approval: false,
    approval_type: '',
    approvers: [],
    remark: '',
  };
  approvalRules.value = [];
  userOptions.value = [];
}
</script>

<template>
  <Modal title="发布应用" width="600px">
    <Spin :spinning="loading">
      <div class="release-form">
        <!-- 应用信息 -->
        <div class="app-info">
          <div class="info-item">
            <span class="label">应用名称：</span>
            <span class="value">{{ application?.name }}</span>
          </div>
          <div class="info-item">
            <span class="label">所属项目：</span>
            <span class="value">{{ application?.project_name }}</span>
          </div>
          <div class="info-item">
            <span class="label">所属模块：</span>
            <span class="value">{{ application?.module_name }}</span>
          </div>
        </div>

        <a-divider />

        <!-- 分支输入 -->
        <div class="form-item">
          <label class="required">发布分支</label>
          <Input
            v-model:value="formData.branch"
            placeholder="请输入发布分支，如：main, master, develop"
            allow-clear
          />
          <div class="form-tip">
            默认分支：{{ application?.build_branch || 'main' }}
          </div>
        </div>

        <!-- 环境选择 -->
        <div class="form-item">
          <label class="required">目标环境</label>
          <Select
            v-model:value="formData.environment"
            placeholder="请选择目标环境"
            style="width: 100%"
          >
            <SelectOption
              v-for="env in environments"
              :key="env.code"
              :value="env.code"
              :disabled="!env.has_pipeline_config"
            >
              {{ env.name }}
              <Tag v-if="!env.has_pipeline_config" color="error" style="margin-left: 4px; font-size: 10px;">
                未配置
              </Tag>
              <Tag v-if="env.requires_approval" color="warning" style="margin-left: 4px; font-size: 10px;">
                需审批
              </Tag>
            </SelectOption>
          </Select>
          <div v-if="environments.length > 0 && !environments.some(e => e.has_pipeline_config)" class="form-tip" style="color: #ff4d4f;">
            当前应用未配置流水线，请先在应用编辑中配置 Pipeline 模板
          </div>
        </div>

        <!-- 版本号 -->
        <div class="form-item">
          <label>发布版本（可选）</label>
          <Input
            v-model:value="formData.version"
            placeholder="如不填写，将从代码库自动获取"
          />
        </div>

        <!-- 审批设置 -->
        <template v-if="formData.require_approval">
          <div class="form-item">
            <label>审批类型</label>
            <Select
              v-model:value="formData.approval_type"
              placeholder="选择审批类型"
              style="width: 100%"
              @change="(val: string) => {
                const rule = approvalRules.find(r => r.code === val);
                if (rule?.approvers?.length) {
                  formData.approvers = rule.approvers.map(a => ({ id: a.id, name: a.name }));
                }
              }"
            >
              <SelectOption
                v-for="rule in approvalRules"
                :key="rule.code"
                :value="rule.code"
              >
                {{ rule.name }} ({{ rule.rule_type }})
              </SelectOption>
            </Select>
          </div>

          <div class="form-item">
            <label class="required">审批人</label>
            <Select
              v-model:value="formData.approvers"
              mode="multiple"
              placeholder="输入用户名搜索并选择审批人"
              style="width: 100%"
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
                  <span class="email" v-if="user.email">{{ user.email }}</span>
                </div>
              </SelectOption>
            </Select>
            <div class="form-tip">
              已选择 {{ formData.approvers.length }} 位审批人
            </div>
          </div>
        </template>

        <!-- 发布说明 -->
        <div class="form-item">
          <label>发布说明</label>
          <Textarea
            v-model:value="formData.remark"
            placeholder="请输入发布说明"
            :rows="3"
            show-count
            :maxlength="256"
          />
        </div>

        <!-- 环境提示 -->
        <div v-if="selectedEnv" class="env-tips">
          <a-alert type="info" show-icon>
            <template #message>
              构建完成后将部署到目标环境
            </template>
          </a-alert>
        </div>
      </div>
    </Spin>
  </Modal>
</template>

<style scoped>
.release-form {
  padding: 0 16px;
}

.app-info {
  background: #f5f5f5;
  padding: 16px;
  border-radius: 4px;
}

.info-item {
  display: flex;
  margin-bottom: 8px;
}

.info-item:last-child {
  margin-bottom: 0;
}

.info-item .label {
  color: #666;
  width: 80px;
}

.info-item .value {
  font-weight: 500;
}

.form-item {
  margin-bottom: 16px;
}

.form-item label {
  display: block;
  margin-bottom: 8px;
  font-weight: 500;
}

.form-item label.required::before {
  content: '*';
  color: #ff4d4f;
  margin-right: 4px;
}

.branch-commit {
  color: #999;
  font-size: 12px;
  margin-left: 8px;
}

.env-tips {
  margin-top: 16px;
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

.form-tip {
  margin-top: 4px;
  color: #999;
  font-size: 12px;
}
</style>
