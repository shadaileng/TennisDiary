import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/login/index.vue'),
    meta: { requiresAuth: false, title: '登录' }
  },
  {
    path: '/',
    component: () => import('@/components/layout/MainLayout.vue'),
    meta: { requiresAuth: true },
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/dashboard/index.vue'),
        meta: { title: '仪表盘', icon: 'HomeIcon' }
      },
      {
        path: 'users',
        name: 'Users',
        component: () => import('@/views/users/index.vue'),
        meta: { title: '用户管理', icon: 'UsersIcon', permission: 'users:list' }
      },
      {
        path: 'roles',
        name: 'Roles',
        component: () => import('@/views/roles/index.vue'),
        meta: { title: '角色管理', icon: 'ShieldCheckIcon', permission: 'roles:list' }
      },
      {
        path: 'admins',
        name: 'Admins',
        component: () => import('@/views/admins/index.vue'),
        meta: { title: '管理员', icon: 'UserGroupIcon', permission: 'admins:list' }
      },
      {
        path: 'diaries',
        name: 'Diaries',
        component: () => import('@/views/diaries/index.vue'),
        meta: { title: '日记管理', icon: 'DocumentTextIcon', permission: 'diaries:list' }
      },
      {
        path: 'gears',
        name: 'Gears',
        component: () => import('@/views/gears/index.vue'),
        meta: { title: '装备管理', icon: 'WrenchIcon', permission: 'gears:list' }
      },
      {
        path: 'weights',
        name: 'Weights',
        component: () => import('@/views/weights/index.vue'),
        meta: { title: '体重管理', icon: 'ScaleIcon', permission: 'weights:list' }
      },
      {
        path: 'analyses',
        name: 'Analyses',
        component: () => import('@/views/analyses/index.vue'),
        meta: { title: '分析报告', icon: 'ChartBarIcon', permission: 'analyses:list' }
      },
      {
        path: 'system',
        name: 'System',
        redirect: '/system/health',
        meta: { title: '系统监控', icon: 'Cog6ToothIcon' },
        children: [
          {
            path: 'health',
            name: 'Health',
            component: () => import('@/views/system/health.vue'),
            meta: { title: '健康检查', permission: 'system:health' }
          },
          {
            path: 'config',
            name: 'Config',
            component: () => import('@/views/system/config.vue'),
            meta: { title: '系统配置', permission: 'system:config' }
          },
          {
            path: 'logs',
            name: 'Logs',
            component: () => import('@/views/system/logs.vue'),
            meta: { title: '日志查看', permission: 'system:logs' }
          },
          {
            path: 'backups',
            name: 'Backups',
            component: () => import('@/views/system/backups.vue'),
            meta: { title: '备份管理', permission: 'system:backup' }
          },
          {
            path: 'event-logs',
            name: 'EventLogs',
            component: () => import('@/views/system/event-logs.vue'),
            meta: { title: '事件日志', permission: 'system:logs' }
          },
          {
            path: 'audit-logs',
            name: 'AuditLogs',
            component: () => import('@/views/system/audit-logs.vue'),
            meta: { title: '审计日志', permission: 'system:config' }
          }
        ]
      }
    ]
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/dashboard'
  }
]

export default routes
