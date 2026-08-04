import type { RouteRecordRaw } from 'vue-router';

const routes: RouteRecordRaw[] = [
  {
    meta: {
      icon: 'mdi:rocket-launch',
      order: 9998,
      title: '发布管理',
    },
    name: 'Release',
    path: '/release',
    children: [
      // 项目管理
      {
        path: '/release/project',
        name: 'ReleaseProject',
        meta: {
          icon: 'mdi:folder-outline',
          title: '项目管理',
        },
        component: () => import('#/views/release/project/index.vue'),
      },
      // 模块管理
      {
        path: '/release/module',
        name: 'ReleaseModule',
        meta: {
          icon: 'mdi:folder-multiple',
          title: '模块管理',
        },
        component: () => import('#/views/release/module/index.vue'),
      },
      // 应用管理
      {
        path: '/release/application',
        name: 'ReleaseApplication',
        meta: {
          icon: 'mdi:application',
          title: '应用管理',
        },
        component: () => import('#/views/release/application/index.vue'),
      },
      // 分隔线
      {
        path: '/release/pipeline-template',
        name: 'ReleasePipelineTemplate',
        meta: {
          icon: 'mdi:file-code-outline',
          title: '流水线模板',
        },
        component: () => import('#/views/release/pipelineTemplate/index.vue'),
      },
      {
        path: '/release/code-repository',
        name: 'ReleaseCodeRepository',
        meta: {
          icon: 'mdi:source-repository',
          title: '代码仓库',
        },
        component: () => import('#/views/release/codeRepository/index.vue'),
      },
      // 审批规则
      {
        path: '/release/approval-rule',
        name: 'ReleaseApprovalRule',
        meta: {
          icon: 'mdi:clipboard-check-outline',
          title: '审批规则',
        },
        component: () => import('#/views/release/approvalRule/index.vue'),
      },
      // 发布记录
      {
        path: '/release/record',
        name: 'ReleaseRecord',
        meta: {
          icon: 'mdi:history',
          title: '发布记录',
        },
        component: () => import('#/views/release/record/index.vue'),
      },
      // 发布统计
      {
        path: '/release/statistics',
        name: 'ReleaseStatistics',
        meta: {
          icon: 'mdi:chart-bar',
          title: '发布统计',
        },
        component: () => import('#/views/release/statistics/index.vue'),
      },
    ],
  },
];

export default routes;
