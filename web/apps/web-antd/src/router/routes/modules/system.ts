import type { RouteRecordRaw } from 'vue-router';

import { $t } from '#/locales';

const routes: RouteRecordRaw[] = [
  {
    meta: {
      icon: 'ion:settings-outline',
      order: 9997,
      title: $t('system.title'),
    },
    name: 'System',
    path: '/system',
    children: [
      {
        path: '/system/user',
        name: 'SystemUser',
        meta: {
          icon: 'mdi:account-group',
          title: $t('system.user.title'),
        },
        component: () => import('#/views/system/user/list.vue'),
      },
      {
        path: '/system/role',
        name: 'SystemRole',
        meta: {
          icon: 'mdi:account-group',
          title: $t('system.role.title'),
        },
        component: () => import('#/views/system/role/list.vue'),
      },
      {
        path: '/system/menu',
        name: 'SystemMenu',
        meta: {
          icon: 'mdi:menu',
          title: $t('system.menu.title'),
        },
        component: () => import('#/views/system/menu/list.vue'),
      },
      {
        path: '/system/dept',
        name: 'SystemDept',
        meta: {
          icon: 'charm:organisation',
          title: $t('system.dept.title'),
        },
        component: () => import('#/views/system/dept/list.vue'),
      },
      {
        path: '/system/post',
        name: 'SystemPost',
        meta: {
          icon: 'charm:organisation',
          title: $t('system.post.title'),
        },
        component: () => import('#/views/system/post/list.vue'),
      },
      {
        path: '/system/dict_type',
        name: 'SystemDictType',
        meta: {
          icon: 'mdi:menu',
          title: '字典列表',
        },
        component: () => import('#/views/system/dict_type/list.vue'),
      },
      {
        path: '/system/dict_data',
        name: 'SystemDictData',
        meta: {
          icon: 'mdi:menu',
          title: '字典数据',
          hideInMenu: true, // 关键配置：设置为 true 时菜单将被隐藏
          // affix: true,
        },
        component: () => import('#/views/system/dict_data/list.vue'),
      },
      {
        path: '/system/config',
        name: 'SystemConfig',
        meta: {
          icon: 'carbon:settings',
          title: $t('system.config.name'),
          authority: ['system:config:query'],
        },
        component: () => import('#/views/system/config/list.vue'),
      },
      // {
      //   path: '/system/tenants',
      //   name: 'SystemTenants',
      //   meta: {
      //     icon: 'mdi:menu',
      //     title: '租户列表',
      //   },
      //   component: () => import('#/views/system/tenants/list.vue'),
      // },
      // {
      //   path: '/system/tenant_package',
      //   name: 'SystemTenantPackage',
      //   meta: {
      //     icon: 'charm:organisation',
      //     title: '租户套餐',
      //   },
      //   component: () => import('#/views/system/tenant_package/list.vue'),
      // },
    ],
  },
];

export default routes;
