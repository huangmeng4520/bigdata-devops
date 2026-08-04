<script lang="ts" setup>
import type { ApprovalRuleApi, ReleaseApplicationApi } from '#/api/release';

import { computed, ref, watch } from 'vue';

import { useVbenModal } from '@vben/common-ui';

import { message, Spin, Tag, Input, Select, SelectOption, Textarea, Alert, Divider } from 'ant-design-vue';

import {
  type Environment,
  type ReleaseParams,
  getAppEnvironments,
  getEffectiveRule,
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

// 匹配到的生效审批规则（只读展示）
const effectiveRule = ref<ApprovalRuleApi.ApprovalRule | null>(null);
const ruleLoading = ref(false);

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

// 监听环境变化，自动判断是否需要审批并加载生效规则
watch(
  () => formData.value.environment,
  (env) => {
    if (env) {
      const envInfo = environments.value.find((e) => e.code === env);
      if (envInfo?.requires_approval) {
        formData.value.require_approval = true;
        // 调用生效规则接口匹配当前应用+环境的审批规则
        loadEffectiveRule(env);
      } else {
        formData.value.require_approval = false;
        effectiveRule.value = null;
      }
    } else {
      effectiveRule.value = null;
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

// 加载生效审批规则（应用×环境级匹配）
async function loadEffectiveRule(environment: string) {
  if (!application.value) return;
  ruleLoading.value = true;
  effectiveRule.value = null;
  try {
    const rule = await getEffectiveRule({
      application_id: application.value.id,
      environment,
    });
    effectiveRule.value = rule || null;
    // 将匹配到的规则信息回填到表单，便于提交时携带
    if (rule) {
      formData.value.approval_type = rule.code;
      formData.value.approvers = (rule.approvers || []).map((a) => ({
        id: a.user_id,
        name: a.username,
      }));
    } else {
      formData.value.approval_type = '';
      formData.value.approvers = [];
    }
  } catch (error) {
    console.error('加载审批规则失败', error);
    effectiveRule.value = null;
  } finally {
    ruleLoading.value = false;
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
  // 需要审批但未匹配到规则时，按免审直发处理（后端会再次校验）

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
    // 审批类型（匹配到的规则编码）
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
  effectiveRule.value = null;
}

// 作用域中文映射
const scopeLabelMap: Record<string, string> = {
  application: '应用级',
  project: '项目级',
  global: '全局',
};
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

        <!-- 审批规则只读展示（当环境需要审批时） -->
        <template v-if="formData.require_approval">
          <div class="form-item">
            <label>审批规则</label>
            <Spin :spinning="ruleLoading">
              <div v-if="effectiveRule" class="rule-info">
                <div class="rule-row">
                  <span class="rule-label">规则名称：</span>
                  <span class="rule-value">{{ effectiveRule.name }}</span>
                  <Tag color="blue" style="margin-left: 8px;">
                    {{ scopeLabelMap[effectiveRule.scope] || effectiveRule.scope }}
                  </Tag>
                </div>
                <div class="rule-row">
                  <span class="rule-label">规则类型：</span>
                  <span class="rule-value">{{ effectiveRule.rule_type_display || effectiveRule.rule_type }}</span>
                </div>
                <div class="rule-row">
                  <span class="rule-label">审批人：</span>
                  <span class="rule-value">
                    <Tag
                      v-for="approver in effectiveRule.approvers"
                      :key="approver.user_id"
                      style="margin-right: 4px; margin-bottom: 4px;"
                    >
                      {{ approver.username }}
                      <span v-if="effectiveRule.rule_type === 'sequential'" style="color: #999; font-size: 11px;">
                        (#{{ approver.order }})
                      </span>
                    </Tag>
                  </span>
                </div>
                <div v-if="effectiveRule.min_approvers" class="rule-row">
                  <span class="rule-label">最少通过：</span>
                  <span class="rule-value">{{ effectiveRule.min_approvers }} 人</span>
                </div>
              </div>
              <a-alert
                v-else-if="!ruleLoading"
                type="warning"
                show-icon
                message="该环境未配置审批规则，将免审直发"
              />
            </Spin>
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

.rule-info {
  background: #fafafa;
  border: 1px solid #f0f0f0;
  border-radius: 4px;
  padding: 12px;
}

.rule-row {
  display: flex;
  align-items: flex-start;
  margin-bottom: 8px;
  line-height: 1.8;
}

.rule-row:last-child {
  margin-bottom: 0;
}

.rule-label {
  color: #666;
  width: 80px;
  flex-shrink: 0;
}

.rule-value {
  font-weight: 500;
  flex: 1;
}
</style>
