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
        path: '/release/environment-strategy',
        name: 'ReleaseEnvironmentStrategy',
        meta: {
          icon: 'mdi:cog-outline',
          title: '环境策略',
        },
        component: () => import('#/views/release/environmentStrategy/index.vue'),
      },
      {
        path: '/release/cd-export',
        name: 'ReleaseCdExport',
        meta: {
          icon: 'mdi:download',
          title: 'CD配置导出',
        },
        component: () => import('#/views/release/cdConfigExport/index.vue'),
      },
    ],
  },
];

export default routes;
