<script lang="ts" setup>
import { onMounted, ref, h } from 'vue';
import { Card, Col, DatePicker, Progress, Row, Select, Spin, Statistic, Table, Tabs, Tag } from 'ant-design-vue';
import type { TableColumnsType } from 'ant-design-vue';
import dayjs from 'dayjs';

import {
  getReleaseStatistics,
  getReleaseTrend,
  getAppReleaseRank,
  ENVIRONMENT_MAP,
} from '#/api/release/record';

// 日期范围
const dateRange = ref<any[]>([
  dayjs().subtract(30, 'day'),
  dayjs(),
]);

// 加载状态
const loading = ref(false);
const trendLoading = ref(false);
const rankLoading = ref(false);

// 统计数据
const statistics = ref<any>({
  total: 0,
  success: 0,
  failed: 0,
  pending: 0,
  today: 0,
  week: 0,
  success_rate: 0,
  environment_stats: [],
  status_stats: [],
});

// 趋势数据
const trendData = ref<any[]>([]);

// 应用排行
const appRank = ref<any[]>([]);

// 表格列定义
const rankColumns: TableColumnsType = [
  {
    title: '排名',
    key: 'rank',
    width: 60,
    customRender: ({ index }) => index + 1,
  },
  {
    title: '应用名称',
    dataIndex: 'application__name',
    width: 180,
  },
  {
    title: '所属项目',
    dataIndex: 'application__project__name',
    width: 120,
  },
  {
    title: '发布次数',
    dataIndex: 'total',
    width: 100,
    sorter: (a, b) => a.total - b.total,
  },
  {
    title: '成功次数',
    dataIndex: 'success',
    width: 100,
  },
  {
    title: '失败次数',
    dataIndex: 'failed',
    width: 100,
  },
  {
    title: '成功率',
    key: 'success_rate',
    width: 120,
    customRender: ({ record }) => {
      const rate = record.total > 0 ? Math.round((record.success / record.total) * 100) : 0;
      return h(Progress, { percent: rate, size: 'small', status: rate >= 80 ? 'success' : 'exception' });
    },
  },
];

// 加载统计数据
async function loadStatistics() {
  loading.value = true;
  try {
    const params: any = {};
    if (dateRange.value && dateRange.value.length === 2) {
      params.start_date = dateRange.value[0].format('YYYY-MM-DD');
      params.end_date = dateRange.value[1].format('YYYY-MM-DD');
    }
    
    const res = await getReleaseStatistics(params);
    statistics.value = res || {};
  } catch (error) {
    console.error('加载统计数据失败', error);
  } finally {
    loading.value = false;
  }
}

// 加载趋势数据
async function loadTrend() {
  trendLoading.value = true;
  try {
    const days = dateRange.value && dateRange.value.length === 2
      ? dateRange.value[1].diff(dateRange.value[0], 'day')
      : 30;
    
    const res = await getReleaseTrend({ days: Math.min(days, 90) });
    trendData.value = res || [];
  } catch (error) {
    console.error('加载趋势数据失败', error);
  } finally {
    trendLoading.value = false;
  }
}

// 加载应用排行
async function loadAppRank() {
  rankLoading.value = true;
  try {
    const days = dateRange.value && dateRange.value.length === 2
      ? dateRange.value[1].diff(dateRange.value[0], 'day')
      : 30;
    
    const res = await getAppReleaseRank({ days: Math.min(days, 90), limit: 10 });
    appRank.value = res || [];
  } catch (error) {
    console.error('加载应用排行失败', error);
  } finally {
    rankLoading.value = false;
  }
}

// 日期变化
function handleDateChange() {
  loadStatistics();
  loadTrend();
  loadAppRank();
}

// 初始化
onMounted(() => {
  loadStatistics();
  loadTrend();
  loadAppRank();
});

// 获取环境名称
function getEnvName(code: string): string {
  return ENVIRONMENT_MAP[code] || code;
}
</script>

<template>
  <div class="release-statistics-page">
    <!-- 筛选区域 -->
    <Card class="filter-card" :bordered="false">
      <Row :gutter="16" align="middle">
        <Col>
          <span class="filter-label">统计时间：</span>
          <DatePicker.RangePicker
            v-model:value="dateRange"
            :allow-clear="false"
            @change="handleDateChange"
          />
        </Col>
      </Row>
    </Card>

    <!-- 统计卡片 -->
    <Row :gutter="16" class="stat-cards">
      <Col :span="4">
        <Card :bordered="false" :loading="loading">
          <Statistic title="总发布次数" :value="statistics.total" />
        </Card>
      </Col>
      <Col :span="4">
        <Card :bordered="false" :loading="loading">
          <Statistic title="成功次数" :value="statistics.success" :value-style="{ color: '#3f8600' }" />
        </Card>
      </Col>
      <Col :span="4">
        <Card :bordered="false" :loading="loading">
          <Statistic title="失败次数" :value="statistics.failed" :value-style="{ color: '#cf1322' }" />
        </Card>
      </Col>
      <Col :span="4">
        <Card :bordered="false" :loading="loading">
          <Statistic title="待处理" :value="statistics.pending" :value-style="{ color: '#faad14' }" />
        </Card>
      </Col>
      <Col :span="4">
        <Card :bordered="false" :loading="loading">
          <Statistic title="今日发布" :value="statistics.today" />
        </Card>
      </Col>
      <Col :span="4">
        <Card :bordered="false" :loading="loading">
          <Statistic title="成功率" :value="statistics.success_rate" suffix="%" />
        </Card>
      </Col>
    </Row>

    <!-- 详情区域 -->
    <Tabs class="detail-tabs">
      <Tabs.TabPane key="env" tab="环境统计">
        <Card :bordered="false" :loading="loading">
          <div class="stat-list">
            <div v-for="item in statistics.environment_stats" :key="item.environment" class="stat-item">
              <span class="stat-label">{{ getEnvName(item.environment) }}</span>
              <Progress :percent="statistics.total > 0 ? Math.round((item.count / statistics.total) * 100) : 0" />
              <span class="stat-value">{{ item.count }} 次</span>
            </div>
          </div>
        </Card>
      </Tabs.TabPane>
      
      <Tabs.TabPane key="status" tab="状态分布">
        <Card :bordered="false" :loading="loading">
          <div class="stat-list">
            <div v-for="item in statistics.status_stats" :key="item.status" class="stat-item">
              <Tag :color="item.status === 'build_success' ? 'success' : (item.status === 'build_failed' ? 'error' : 'processing')">
                {{ item.status }}
              </Tag>
              <Progress :percent="statistics.total > 0 ? Math.round((item.count / statistics.total) * 100) : 0" />
              <span class="stat-value">{{ item.count }} 次</span>
            </div>
          </div>
        </Card>
      </Tabs.TabPane>

      <Tabs.TabPane key="trend" tab="发布趋势">
        <Card :bordered="false" :loading="trendLoading">
          <Table
            :columns="[
              { title: '日期', dataIndex: 'date', width: 120 },
              { title: '总发布', dataIndex: 'total', width: 100 },
              { title: '成功', dataIndex: 'success', width: 100 },
              { title: '失败', dataIndex: 'failed', width: 100 },
            ]"
            :data-source="trendData"
            :pagination="{ pageSize: 10 }"
            size="small"
            row-key="date"
          />
        </Card>
      </Tabs.TabPane>

      <Tabs.TabPane key="rank" tab="应用排行">
        <Card :bordered="false" :loading="rankLoading">
          <Table
            :columns="rankColumns"
            :data-source="appRank"
            :pagination="false"
            size="small"
            row-key="application__id"
          />
        </Card>
      </Tabs.TabPane>
    </Tabs>
  </div>
</template>

<style scoped>
.release-statistics-page {
  padding: 16px;
}

.filter-card {
  margin-bottom: 16px;
}

.filter-label {
  margin-right: 8px;
}

.stat-cards {
  margin-bottom: 16px;
}

.stat-cards .ant-card {
  text-align: center;
}

.detail-tabs {
  background: #fff;
  padding: 16px;
  border-radius: 2px;
}

.stat-list {
  max-height: 400px;
  overflow-y: auto;
}

.stat-item {
  display: flex;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid #f0f0f0;
}

.stat-item:last-child {
  border-bottom: none;
}

.stat-label {
  min-width: 80px;
  font-weight: 500;
}

.stat-value {
  min-width: 60px;
  text-align: right;
  margin-left: 16px;
}

.stat-item .ant-progress {
  flex: 1;
  margin: 0 16px;
}
</style>
