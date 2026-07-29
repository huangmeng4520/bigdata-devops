<script lang="ts" setup>
import type { TableColumnsType } from 'ant-design-vue';

import type { ReleaseRecord } from '#/api/release/record';

import { h, onMounted, reactive, ref } from 'vue';
import { useRouter } from 'vue-router';

import {
  Badge,
  Button,
  Card,
  Form,
  Input,
  message,
  RangePicker,
  Select,
  Table,
  Tag,
} from 'ant-design-vue';

import {
  cancelRelease,
  createAIAnalysis,
  ENVIRONMENT_OPTIONS,
  getReleaseList,
  RELEASE_STATUS_MAP,
  retryBuild,
} from '#/api/release/record';
import { hasPermission } from '#/utils/permission';

import ApprovalModal from './modules/ApprovalModal.vue';
import BuildLogModal from './modules/BuildLogModal.vue';

// 搜索表单
const searchForm = reactive({
  application_name: '',
  environment: undefined as string | undefined,
  status: undefined as string | undefined,
  released_by: '',
  dateRange: [] as any[],
});

// 分页
const pagination = reactive({
  current: 1,
  pageSize: 20,
  total: 0,
  showSizeChanger: true,
  showQuickJumper: true,
  showTotal: (total: number) => `共 ${total} 条`,
});

// 加载状态
const loading = ref(false);

// 数据列表
const tableData = ref<ReleaseRecord[]>([]);

// 弹窗引用
const router = useRouter();
const buildLogModalRef = ref();
const approvalModalRef = ref();

// 表格列定义
const columns: TableColumnsType = [
  {
    title: '应用名称',
    dataIndex: 'application_name',
    width: 180,
    fixed: 'left',
  },
  {
    title: '所属项目',
    dataIndex: 'project_name',
    width: 120,
  },
  {
    title: '所属模块',
    dataIndex: 'module_name',
    width: 100,
  },
  {
    title: '发布分支',
    dataIndex: 'branch',
    width: 120,
  },
  {
    title: '目标环境',
    dataIndex: 'environment_display',
    width: 100,
  },
  {
    title: '构建号',
    dataIndex: 'jenkins_build_number',
    width: 80,
    customRender: ({ text }) => (text ? `#${text}` : '-'),
  },
  {
    title: '状态',
    dataIndex: 'status',
    width: 100,
    customRender: ({ text }) => {
      const statusInfo = RELEASE_STATUS_MAP[text] || { text, color: 'default' };
      return h(Badge, {
        status: statusInfo.color as any,
        text: statusInfo.text,
      });
    },
  },
  {
    title: '审批状态',
    dataIndex: 'require_approval',
    width: 100,
    customRender: ({ record }) => {
      if (!record.require_approval) return '-';
      if (record.status === 'approval_pending') {
        return h(Tag, { color: 'warning' }, () => '待审批');
      }
      if (record.approval_user) {
        return h(Tag, { color: 'success' }, () => record.approval_user);
      }
      return '-';
    },
  },
  {
    title: '发布人',
    dataIndex: 'released_by',
    width: 100,
  },
  {
    title: '发布时间',
    dataIndex: 'create_time',
    width: 160,
  },
  {
    title: '操作',
    key: 'action',
    width: 200,
    fixed: 'right',
  },
];

// 加载数据
async function loadData() {
  loading.value = true;
  try {
    const params: any = {
      page: pagination.current,
      page_size: pagination.pageSize,
    };

    if (searchForm.application_name) {
      params.application_name = searchForm.application_name;
    }
    if (searchForm.environment) {
      params.environment = searchForm.environment;
    }
    if (searchForm.status) {
      params.status = searchForm.status;
    }
    if (searchForm.released_by) {
      params.released_by = searchForm.released_by;
    }
    if (searchForm.dateRange && searchForm.dateRange.length === 2) {
      params.start_date = searchForm.dateRange[0].format('YYYY-MM-DD');
      params.end_date = searchForm.dateRange[1].format('YYYY-MM-DD');
    }

    const res = await getReleaseList(params);
    // 后端返回格式: {total: number, items: [...]}
    tableData.value = res.items || [];
    pagination.total = res.total || 0;
  } catch (error) {
    message.error('加载数据失败');
    console.error(error);
  } finally {
    loading.value = false;
  }
}

// 搜索
function handleSearch() {
  pagination.current = 1;
  loadData();
}

// 重置
function handleReset() {
  Object.assign(searchForm, {
    application_name: '',
    environment: undefined,
    status: undefined,
    released_by: '',
    dateRange: [],
  });
  pagination.current = 1;
  loadData();
}

// 表格变化
function handleTableChange(pag: any) {
  pagination.current = pag.current;
  pagination.pageSize = pag.pageSize;
  loadData();
}

// 查看日志
function handleViewLog(record: ReleaseRecord) {
  buildLogModalRef.value?.open(record.id);
}

// 取消发布
async function handleCancel(record: ReleaseRecord) {
  try {
    await cancelRelease(record.id);
    message.success('已取消发布');
    loadData();
  } catch (error: any) {
    message.error(error?.response?.data?.error || '取消失败');
  }
}

// 重试构建
async function handleRetry(record: ReleaseRecord) {
  try {
    await retryBuild(record.id);
    message.success('已重新触发构建');
    loadData();
  } catch (error: any) {
    message.error(error?.response?.data?.error || '重试失败');
  }
}

// AI 分析构建失败
async function handleAIAnalyze(record: ReleaseRecord) {
  try {
    const res = await createAIAnalysis(record.id);
    const conversationId = res.conversation_id ?? res;
    router.push({
      path: '/ai/chat',
      query: { conversation_id: conversationId, auto_send: '1' },
    });
  } catch (error: any) {
    message.error(
      error?.response?.data?.error || error?.message || '创建 AI 分析失败',
    );
  }
}

// 打开审批弹窗
function handleApprove(record: ReleaseRecord, type: 'approve' | 'reject') {
  approvalModalRef.value?.open(record, type);
}

// 审批成功
function handleApprovalSuccess() {
  loadData();
}

// 获取状态颜色
function getStatusColor(status: string): string {
  return RELEASE_STATUS_MAP[status]?.color || 'default';
}

// 判断是否可以取消
function canCancel(record: ReleaseRecord): boolean {
  return ['approval_pending', 'building', 'pending'].includes(record.status);
}

// 判断是否可以重试
function canRetry(record: ReleaseRecord): boolean {
  return ['build_failed', 'cancelled'].includes(record.status);
}

// 判断是否可以审批
function canApprove(record: ReleaseRecord): boolean {
  return record.status === 'approval_pending';
}

// 判断是否可以查看日志
function canViewLog(record: ReleaseRecord): boolean {
  return !!record.jenkins_build_number;
}

// 初始化
onMounted(() => {
  loadData();
});
</script>

<template>
  <div class="release-record-page">
    <!-- 搜索区域 -->
    <Card class="search-card" :bordered="false">
      <Form layout="inline">
        <Form.Item label="应用名称">
          <Input
            v-model:value="searchForm.application_name"
            placeholder="请输入应用名称"
            allow-clear
            style="width: 180px"
            @press-enter="handleSearch"
          />
        </Form.Item>
        <Form.Item label="目标环境">
          <Select
            v-model:value="searchForm.environment"
            placeholder="请选择环境"
            allow-clear
            style="width: 120px"
            :options="ENVIRONMENT_OPTIONS"
          />
        </Form.Item>
        <Form.Item label="发布状态">
          <Select
            v-model:value="searchForm.status"
            placeholder="请选择状态"
            allow-clear
            style="width: 120px"
          >
            <Select.Option
              v-for="(info, key) in RELEASE_STATUS_MAP"
              :key="key"
              :value="key"
            >
              {{ info.text }}
            </Select.Option>
          </Select>
        </Form.Item>
        <Form.Item label="发布人">
          <Input
            v-model:value="searchForm.released_by"
            placeholder="请输入发布人"
            allow-clear
            style="width: 120px"
            @press-enter="handleSearch"
          />
        </Form.Item>
        <Form.Item label="发布时间">
          <RangePicker
            v-model:value="searchForm.dateRange"
            style="width: 240px"
          />
        </Form.Item>
        <Form.Item>
          <Button type="primary" @click="handleSearch">查询</Button>
          <Button style="margin-left: 8px" @click="handleReset">重置</Button>
        </Form.Item>
      </Form>
    </Card>

    <!-- 数据表格 -->
    <Card class="table-card" :bordered="false">
      <Table
        :columns="columns"
        :data-source="tableData"
        :loading="loading"
        :pagination="pagination"
        :scroll="{ x: 1500 }"
        row-key="id"
        @change="handleTableChange"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'action'">
            <Button
              v-if="hasPermission('release:release_record:query')"
              type="link"
              size="small"
              @click="handleViewLog(record)"
              :disabled="!canViewLog(record)"
            >
              查看日志
            </Button>
            <Button
              v-if="
                canApprove(record) && hasPermission('release:release_record:approve')
              "
              type="link"
              size="small"
              @click="handleApprove(record, 'approve')"
            >
              通过
            </Button>
            <Button
              v-if="
                canApprove(record) && hasPermission('release:release_record:reject')
              "
              type="link"
              size="small"
              danger
              @click="handleApprove(record, 'reject')"
            >
              拒绝
            </Button>
            <Button
              v-if="record.status === 'build_failed'"
              type="link"
              size="small"
              @click="handleAIAnalyze(record)"
            >
              AI 分析
            </Button>
            <Button
              v-if="canRetry(record) && hasPermission('release:release_record:retry')"
              type="link"
              size="small"
              @click="handleRetry(record)"
            >
              重试
            </Button>
            <Button
              v-if="canCancel(record) && hasPermission('release:release_record:cancel')"
              type="link"
              size="small"
              danger
              @click="handleCancel(record)"
            >
              取消
            </Button>
          </template>
        </template>
      </Table>
    </Card>

    <!-- 构建日志弹窗 -->
    <BuildLogModal ref="buildLogModalRef" />

    <!-- 审批弹窗 -->
    <ApprovalModal ref="approvalModalRef" @success="handleApprovalSuccess" />
  </div>
</template>

<style scoped>
.release-record-page {
  padding: 16px;
}

.search-card {
  margin-bottom: 16px;
}

.table-card {
  /* 表格卡片样式 */
}
</style>
