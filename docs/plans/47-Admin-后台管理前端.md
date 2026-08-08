> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 47-Admin |
> | 文档版本 | v1.0.0 |
> | 文档状态 | 📋 待执行 |
> | 最后更新 | 2026-08-08 |
> | 对应功能/内容 | 后台管理前端（Vite + Vue 3 + Tailwind CSS） |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-08-08 | v1.0.0 | 初版 |
>
> **关联文档**：[B2 后台管理API总纲](./43-B2-后台管理API总纲.md)

# Phase Admin：后台管理前端

## 一、目标

基于 Vite + Vue 3 + TypeScript + Tailwind CSS 构建后台管理界面，实现与后端管理API的完整对接。

## 二、需求概述

| 需求项 | 说明 |
|--------|------|
| 项目名称 | admin |
| 技术栈 | Vite 5 + Vue 3.4 + TypeScript 5 |
| 路由管理 | Vue Router 4 |
| 状态管理 | Pinia 2 |
| UI组件 | 纯 Tailwind CSS（无组件库） |
| 登录方式 | 账号密码登录 + 微信扫码登录 |
| 部署方式 | 独立部署（Nginx） |

## 三、目录结构

### 3.1 项目结构

```
admin/
├── public/
├── src/
│   ├── api/                  # API接口
│   │   ├── index.ts          # axios实例
│   │   ├── auth.ts           # 认证相关
│   │   ├── users.ts          # 用户管理
│   │   ├── roles.ts          # 角色管理
│   │   ├── admins.ts         # 管理员管理
│   │   ├── diaries.ts        # 日记管理
│   │   ├── gears.ts          # 装备管理
│   │   ├── weights.ts        # 体重管理
│   │   ├── analyses.ts       # 分析管理
│   │   └── system.ts         # 系统监控
│   ├── assets/               # 静态资源
│   │   └── logo.svg
│   ├── components/           # 公共组件
│   │   ├── layout/           # 布局组件
│   │   │   ├── MainLayout.vue
│   │   │   ├── Sidebar.vue
│   │   │   ├── Header.vue
│   │   │   └── Breadcrumb.vue
│   │   ├── common/           # 通用组件
│   │   │   ├── Button.vue
│   │   │   ├── Input.vue
│   │   │   ├── Select.vue
│   │   │   ├── Table.vue
│   │   │   ├── Modal.vue
│   │   │   ├── Pagination.vue
│   │   │   ├── Card.vue
│   │   │   ├── Tag.vue
│   │   │   ├── Switch.vue
│   │   │   ├── Tabs.vue
│   │   │   └── Loading.vue
│   │   └── icons/            # 图标组件
│   │       └── index.ts
│   ├── composables/          # 组合式函数
│   │   ├── useAuth.ts        # 认证相关
│   │   ├── useTable.ts       # 表格相关
│   │   ├── useModal.ts       # 弹窗相关
│   │   └── usePermission.ts  # 权限相关
│   ├── router/               # 路由配置
│   │   ├── index.ts
│   │   └── routes.ts
│   ├── stores/               # Pinia状态
│   │   ├── auth.ts           # 认证状态
│   │   └── app.ts            # 应用状态
│   ├── styles/               # 样式
│   │   ├── main.css          # Tailwind CSS主样式
│   │   └── variables.css     # CSS变量
│   ├── types/                # TypeScript类型
│   │   ├── api.ts            # API响应类型
│   │   ├── model.ts          # 数据模型类型
│   │   └── index.ts
│   ├── utils/                # 工具函数
│   │   ├── request.ts        # HTTP请求封装
│   │   ├── storage.ts        # 本地存储
│   │   ├── format.ts         # 格式化工具
│   │   └── validation.ts     # 表单验证
│   ├── views/                # 页面视图
│   │   ├── login/
│   │   │   └── index.vue
│   │   ├── dashboard/
│   │   │   └── index.vue
│   │   ├── users/
│   │   │   ├── index.vue
│   │   │   └── components/
│   │   │       └── UserDetail.vue
│   │   ├── roles/
│   │   │   ├── index.vue
│   │   │   └── components/
│   │   │       ├── RoleForm.vue
│   │   │       └── PermissionTree.vue
│   │   ├── admins/
│   │   │   ├── index.vue
│   │   │   └── components/
│   │   │       └── AdminForm.vue
│   │   ├── diaries/
│   │   │   └── index.vue
│   │   ├── gears/
│   │   │   └── index.vue
│   │   ├── weights/
│   │   │   └── index.vue
│   │   ├── analyses/
│   │   │   └── index.vue
│   │   └── system/
│   │       ├── health.vue
│   │       ├── logs.vue
│   │       └── backups.vue
│   ├── App.vue
│   └── main.ts
├── index.html
├── package.json
├── tailwind.config.js
├── tsconfig.json
├── vite.config.ts
├── .env
├── .env.development
├── .env.production
└── nginx.conf
```

### 3.2 文件说明

| 目录 | 说明 |
|------|------|
| `api/` | 按模块组织API接口，统一封装axios |
| `components/common/` | 纯Tailwind CSS实现的通用组件 |
| `components/layout/` | 布局组件（侧边栏、头部、主内容区） |
| `composables/` | Vue 3组合式函数 |
| `router/` | 路由配置，支持权限校验 |
| `stores/` | Pinia状态管理 |
| `types/` | TypeScript类型定义 |
| `views/` | 页面视图，按功能模块分组 |

## 四、技术栈详情

### 4.1 依赖列表

```json
{
  "dependencies": {
    "vue": "^3.4.21",
    "vue-router": "^4.3.0",
    "pinia": "^2.1.7",
    "axios": "^1.7.0",
    "dayjs": "^1.11.0",
    "@heroicons/vue": "^2.1.0"
  },
  "devDependencies": {
    "vite": "^5.4.0",
    "typescript": "^5.5.0",
    "vue-tsc": "^2.0.0",
    "tailwindcss": "^3.4.0",
    "postcss": "^8.4.0",
    "autoprefixer": "^10.4.0",
    "@vitejs/plugin-vue": "^5.0.0"
  }
}
```

### 4.2 版本说明

| 分类 | 技术 | 版本 |
|------|------|------|
| 构建工具 | Vite | ^5.4.0 |
| 前端框架 | Vue 3 | ^3.4.21 |
| 类型检查 | TypeScript | ^5.5.0 |
| 路由 | Vue Router | ^4.3.0 |
| 状态管理 | Pinia | ^2.1.7 |
| 样式 | Tailwind CSS | ^3.4.0 |
| HTTP请求 | Axios | ^1.7.0 |
| 图标 | Heroicons | ^2.1.0 |
| 日期处理 | Day.js | ^1.11.0 |

## 五、页面功能设计

### 5.1 登录页 `/login`

**功能**：
- 账号密码登录
- 微信扫码登录
- 记住登录状态

**布局**：
```
┌─────────────────────────────────────────┐
│           Tennis Diary Admin            │
├─────────────────────────────────────────┤
│  ┌─────────────────────────────────┐   │
│  │  [Tab] 账号密码  微信扫码       │   │
│  ├─────────────────────────────────┤   │
│  │  账号密码登录:                   │   │
│  │  [用户名] ___________________   │   │
│  │  [密码]   ___________________   │   │
│  │  [✓ 记住我]                     │   │
│  │  [登录按钮]                     │   │
│  ├─────────────────────────────────┤   │
│  │  微信扫码登录:                   │   │
│  │  [二维码区域]                   │   │
│  │  请使用微信扫码登录             │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

### 5.2 仪表盘 `/dashboard`

**功能**：
- 数据概览卡片（用户数、日记数、装备数、今日打卡）
- 最近活动列表
- 系统状态（磁盘、数据库、运行时长）

**布局**：
```
┌─────────────────────────────────────────────────────────┐
│  仪表盘                                                  │
├─────────────┬─────────────┬─────────────┬───────────────┤
│  用户总数   │  日记总数   │  装备总数   │  今日打卡     │
│    128      │    456      │     89      │     12        │
├─────────────┴─────────────┴─────────────┴───────────────┤
│  ┌──────────────────────┬──────────────────────────────┐│
│  │  最近活动            │  系统状态                    ││
│  │  - 用户xxx创建了日记 │  磁盘使用: 45%              ││
│  │  - 用户yyy上传了装备 │  数据库: 12.5MB             ││
│  │  ...                 │  运行时长: 7天               ││
│  └──────────────────────┴──────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
```

### 5.3 用户管理 `/users`

**功能**：
- 用户列表（分页、搜索、筛选）
- 查看用户详情
- 查看用户日记/装备等数据

**列表字段**：
| 字段 | 说明 |
|------|------|
| ID | 用户ID |
| 昵称 | 用户昵称 |
| 头像 | 用户头像缩略图 |
| 性别 | 性别 |
| 日记数 | 该用户日记总数 |
| 注册时间 | 创建时间 |
| 操作 | 查看详情 |

### 5.4 角色管理 `/roles`

**功能**：
- 角色列表
- 创建角色
- 编辑角色（名称、描述、权限）
- 删除角色（系统角色不可删除）

**列表字段**：
| 字段 | 说明 |
|------|------|
| 角色名 | 角色名称 |
| 编码 | 角色编码 |
| 描述 | 角色描述 |
| 权限数 | 权限数量 |
| 类型 | 系统/自定义 |
| 操作 | 编辑/删除 |

### 5.5 管理员管理 `/admins`

**功能**：
- 管理员列表
- 创建管理员
- 编辑管理员（昵称、角色）
- 启用/禁用
- 重置密码
- 删除管理员

**列表字段**：
| 字段 | 说明 |
|------|------|
| ID | 管理员ID |
| 用户名 | 登录用户名 |
| 昵称 | 显示昵称 |
| 角色 | 所属角色 |
| 状态 | 启用/禁用 |
| 最后登录 | 最后登录时间 |
| 操作 | 编辑/重置密码/禁用/删除 |

### 5.6 数据管理页面

#### 日记管理 `/diaries`
| 字段 | 说明 |
|------|------|
| ID | 日记ID |
| 用户 | 用户昵称 |
| 日期 | 日记日期 |
| 类型 | 训练/比赛等 |
| 时长 | 训练时长 |
| 操作 | 查看/删除 |

#### 装备管理 `/gears`
| 字段 | 说明 |
|------|------|
| ID | 装备ID |
| 用户 | 用户昵称 |
| 名称 | 装备名称 |
| 种类 | 装备种类 |
| 价格 | 购买价格 |
| 操作 | 查看/删除 |

#### 体重管理 `/weights`
| 字段 | 说明 |
|------|------|
| ID | 记录ID |
| 用户 | 用户昵称 |
| 日期 | 记录日期 |
| 体重 | 体重值 |
| 操作 | 删除 |

#### 分析报告 `/analyses`
| 字段 | 说明 |
|------|------|
| ID | 报告ID |
| 用户 | 用户昵称 |
| 日期 | 分析日期 |
| 类型 | 分析类型 |
| 评分 | 分析评分 |
| 操作 | 查看/删除 |

### 5.7 系统监控页面

#### 健康检查 `/system/health`
- 系统状态
- 数据库连接状态
- 磁盘使用情况
- 运行时长

#### 日志查看 `/system/logs`
- 日志列表（支持按文件/级别/关键字筛选）
- 实时刷新
- 日志详情查看

#### 备份管理 `/system/backups`
- 备份列表
- 创建备份
- 恢复备份

## 六、路由设计

### 6.1 路由配置

```typescript
// router/routes.ts
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
```

### 6.2 路由守卫

```typescript
// router/index.ts
import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import routes from './routes'

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()
  
  // 需要认证的页面
  if (to.meta.requiresAuth && !authStore.token) {
    next({ name: 'Login', query: { redirect: to.fullPath } })
    return
  }
  
  // 已登录访问登录页，跳转首页
  if (to.name === 'Login' && authStore.token) {
    next({ name: 'Dashboard' })
    return
  }
  
  // 权限校验
  if (to.meta.permission && !authStore.hasPermission(to.meta.permission as string)) {
    next({ name: 'Dashboard' })
    return
  }
  
  next()
})

export default router
```

## 七、状态管理设计

### 7.1 认证状态

```typescript
// stores/auth.ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { AdminInfo } from '@/types'
import { login, logout, getAdminInfo } from '@/api/auth'
import { getToken, setToken, removeToken } from '@/utils/storage'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(getToken())
  const admin = ref<AdminInfo | null>(null)
  
  const isLoggedIn = computed(() => !!token.value)
  const permissions = computed(() => admin.value?.role?.permissions || [])
  
  async function doLogin(username: string, password: string) {
    const res = await login({ username, password })
    token.value = res.access_token
    admin.value = res.admin
    setToken(res.access_token)
    return res
  }
  
  async function fetchAdminInfo() {
    if (!token.value) return
    const res = await getAdminInfo()
    admin.value = res
  }
  
  function hasPermission(perm: string) {
    if (admin.value?.role?.code === 'superadmin') return true
    return permissions.value.includes(perm)
  }
  
  function doLogout() {
    token.value = null
    admin.value = null
    removeToken()
  }
  
  return { token, admin, isLoggedIn, permissions, doLogin, fetchAdminInfo, hasPermission, doLogout }
})
```

### 7.2 应用状态

```typescript
// stores/app.ts
import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAppStore = defineStore('app', () => {
  const sidebarCollapsed = ref(false)
  const loading = ref(false)
  
  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }
  
  function setLoading(val: boolean) {
    loading.value = val
  }
  
  return { sidebarCollapsed, loading, toggleSidebar, setLoading }
})
```

## 八、API接口封装

### 8.1 Axios实例

```typescript
// api/index.ts
import axios from 'axios'
import { useAuthStore } from '@/stores/auth'
import { ElMessage } from 'element-plus' // 不使用，改用自定义toast

const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 15000
})

request.interceptors.request.use(config => {
  const authStore = useAuthStore()
  if (authStore.token) {
    config.headers.Authorization = `Bearer ${authStore.token}`
  }
  return config
})

request.interceptors.response.use(
  response => response.data,
  error => {
    const status = error.response?.status
    const message = error.response?.data?.detail || '请求失败'
    
    if (status === 401) {
      const authStore = useAuthStore()
      authStore.doLogout()
      window.location.href = '/login'
    }
    
    return Promise.reject(new Error(message))
  }
)

export default request
```

### 8.2 API模块示例

```typescript
// api/auth.ts
import request from './index'
import type { LoginRequest, LoginResponse, AdminInfo } from '@/types'

export function login(data: LoginRequest): Promise<LoginResponse> {
  return request.post('/api/admin/auth/login', data)
}

export function getAdminInfo(): Promise<AdminInfo> {
  return request.get('/api/admin/auth/me')
}

export function updatePassword(data: { old_password: string; new_password: string }) {
  return request.put('/api/admin/auth/password', data)
}
```

```typescript
// api/users.ts
import request from './index'
import type { UserListResponse, UserInfo } from '@/types'

export function getUsers(params: { offset?: number; limit?: number }): Promise<UserListResponse> {
  return request.get('/api/admin/users', { params })
}

export function getUser(userId: number): Promise<UserInfo> {
  return request.get(`/api/admin/users/${userId}`)
}

export function deleteUser(userId: number) {
  return request.delete(`/api/admin/users/${userId}`)
}
```

## 九、环境变量配置

### 9.1 环境变量文件

```bash
# .env
VITE_APP_TITLE=Tennis Diary Admin
VITE_APP_VERSION=1.0.0

# .env.development
VITE_API_BASE_URL=http://localhost:8000

# .env.production
VITE_API_BASE_URL=https://api.example.com
```

### 9.2 类型声明

```typescript
// env.d.ts
/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string
  readonly VITE_APP_TITLE: string
  readonly VITE_APP_VERSION: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
```

## 十、部署配置

### 10.1 Nginx配置

```nginx
# nginx.conf
server {
    listen 80;
    server_name admin.example.com;

    root /usr/share/nginx/html;
    index index.html;

    # Gzip压缩
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;

    # Vue Router history模式
    location / {
        try_files $uri $uri/ /index.html;
    }

    # 静态资源缓存
    location /assets {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # API代理
    location /api {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 禁止访问隐藏文件
    location ~ /\. {
        deny all;
    }
}
```

### 10.2 Docker配置（可选）

```dockerfile
# Dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

## 十一、测试用例

### 11.1 测试文件结构

```
tests/
├── components/
│   ├── Button.spec.ts
│   ├── Table.spec.ts
│   └── Modal.spec.ts
├── views/
│   ├── login.spec.ts
│   ├── dashboard.spec.ts
│   └── users.spec.ts
├── stores/
│   └── auth.spec.ts
└── utils/
    └── request.spec.ts
```

### 11.2 关键测试用例

| 模块 | 测试用例 | 验证点 |
|------|---------|--------|
| 登录 | test_login_success | 登录成功跳转 |
| 登录 | test_login_failed | 登录失败提示 |
| 认证 | test_token_storage | token正确存储 |
| 认证 | test_auto_logout | token过期自动登出 |
| 权限 | test_permission_check | 权限校验正确 |
| 用户列表 | test_fetch_users | 获取用户列表 |
| 用户列表 | test_pagination | 分页功能正常 |

## 十二、验收标准

### 12.1 功能验收

| 功能 | 验收标准 |
|------|---------|
| 登录 | 支持账号密码和微信扫码登录 |
| 仪表盘 | 正确显示数据概览和系统状态 |
| 用户管理 | 列表分页、查看详情正常 |
| 角色管理 | CRUD操作正常，系统角色保护 |
| 管理员管理 | 创建/编辑/删除/重置密码正常 |
| 数据管理 | 日记/装备/体重/分析列表正常 |
| 系统监控 | 健康检查/日志/备份功能正常 |
| 权限控制 | 无权限菜单隐藏，接口拦截正确 |

### 12.2 代码质量验收

| 检查项 | 标准 |
|--------|------|
| TypeScript | 无类型错误 |
| ESLint | 无报错 |
| 构建 | `npm run build` 成功 |
| 测试 | 核心功能测试通过 |

## 十三、实施步骤

### Phase Admin-1: 项目初始化（1-2天）

1. 创建admin目录
2. 初始化Vite + Vue 3 + TypeScript项目
3. 配置Tailwind CSS
4. 配置Vue Router和Pinia
5. 创建基础目录结构
6. 实现通用组件（Button、Input、Table等）

### Phase Admin-2: 布局与登录（2-3天）

1. 实现MainLayout布局
2. 实现Sidebar侧边栏
3. 实现Header头部
4. 实现登录页（账号密码+微信扫码）
5. 实现路由守卫

### Phase Admin-3: 仪表盘（1-2天）

1. 实现仪表盘页面
2. 对接系统统计API
3. 显示最近活动和系统状态

### Phase Admin-4: 管理功能（3-4天）

1. 实现用户管理页面
2. 实现角色管理页面
3. 实现管理员管理页面
4. 对接相关API

### Phase Admin-5: 数据管理（2-3天）

1. 实现日记管理页面
2. 实现装备管理页面
3. 实现体重管理页面
4. 实现分析报告页面
5. 对接相关API

### Phase Admin-6: 系统监控（2-3天）

1. 实现健康检查页面
2. 实现日志查看页面
3. 实现备份管理页面
4. 对接相关API

### Phase Admin-7: 测试与部署（2-3天）

1. 编写测试用例
2. 配置Nginx
3. 编写部署文档
4. 优化和修复

## 十四、时间估算

| 阶段 | 内容 | 预计时间 |
|------|------|---------|
| Phase Admin-1 | 项目初始化 + 路由 + 布局 | 1-2天 |
| Phase Admin-2 | 登录页（账号密码+微信扫码） | 2-3天 |
| Phase Admin-3 | 仪表盘 + 通用组件 | 1-2天 |
| Phase Admin-4 | 用户/角色/管理员管理 | 3-4天 |
| Phase Admin-5 | 数据管理（日记/装备/体重等） | 2-3天 |
| Phase Admin-6 | 系统监控（健康/日志/备份） | 2-3天 |
| Phase Admin-7 | 测试 + 部署配置 | 2-3天 |
| **总计** | | **13-20天** |

## 十五、提交规范

```bash
feat(admin): 初始化后台管理前端项目

- 创建admin目录结构
- 配置Vite + Vue 3 + TypeScript
- 配置Tailwind CSS
- 配置Vue Router和Pinia
- 实现通用组件
```
