> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 47-Admin |
> | 文档版本 | v2.0.0 |
> | 文档状态 | ✅ 已完成 |
> | 最后更新 | 2026-08-21 |
> | 对应功能/内容 | 后台管理前端（Vite + Vue 3 + Tailwind CSS） |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-08-08 | v1.0.0 | 初版 |
> | 2026-08-21 | v2.0.0 | 根据实际代码更新：技术栈升级、部署改为 Cloudflare Workers、功能模块完善 |
>
> **关联文档**：[B2 后台管理API总纲](./43-B2-后台管理API总纲.md)

# Phase Admin：后台管理前端

## 一、目标

基于 Vite + Vue 3 + TypeScript + Tailwind CSS 构建后台管理界面，实现与后端管理API的完整对接。

## 二、需求概述

| 需求项 | 说明 |
|--------|------|
| 项目名称 | admin |
| 技术栈 | Vite 8 + Vue 3.5 + TypeScript 6 |
| 路由管理 | Vue Router 4 |
| 状态管理 | Pinia 4 |
| UI组件 | 纯 Tailwind CSS（无组件库） |
| 登录方式 | 账号密码登录 |
| 部署方式 | Cloudflare Workers Pages/Assets 托管（SPA 自动 fallback） |

## 三、目录结构

### 3.1 项目结构

```
admin/
├── public/
├── src/
│   ├── api/                  # API接口
│   │   ├── index.ts          # axios实例 + 拦截器
│   │   ├── auth.ts           # 认证相关
│   │   ├── users.ts          # 用户管理
│   │   ├── roles.ts          # 角色管理
│   │   ├── admins.ts         # 管理员管理
│   │   ├── diaries.ts        # 日记管理
│   │   ├── gears.ts          # 装备管理
│   │   ├── weights.ts        # 体重管理
│   │   ├── analyses.ts       # 分析管理
│   │   ├── checkins.ts       # 打卡管理
│   │   ├── posts.ts          # 帖子管理
│   │   ├── events.ts         # 事件管理
│   │   ├── system.ts         # 系统监控
│   │   └── config.ts         # 系统配置
│   ├── assets/               # 静态资源
│   ├── components/           # 公共组件
│   │   ├── layout/           # 布局组件
│   │   │   ├── MainLayout.vue
│   │   │   ├── Sidebar.vue
│   │   │   ├── Header.vue
│   │   │   └── Breadcrumb.vue
│   │   └── common/           # 通用组件
│   │       ├── Table.vue
│   │       ├── Modal.vue
│   │       ├── Pagination.vue
│   │       ├── StatCard.vue
│   │       ├── Toast.vue
│   │       └── Loading.vue
│   ├── composables/          # 组合式函数
│   │   └── useActionLock.ts  # 操作锁（防重复提交）
│   ├── router/               # 路由配置
│   │   ├── index.ts
│   │   └── routes.ts
│   ├── stores/               # Pinia状态
│   │   ├── index.ts
│   │   ├── auth.ts           # 认证状态
│   │   ├── app.ts            # 应用状态
│   │   └── toast.ts          # Toast状态
│   ├── styles/               # 样式
│   │   └── main.css          # Tailwind CSS主样式
│   ├── types/                # TypeScript类型
│   │   └── api.ts            # API响应类型
│   ├── utils/                # 工具函数
│   │   └── date.ts           # 日期格式化（东八区）
│   ├── views/                # 页面视图
│   │   ├── login/
│   │   │   └── index.vue
│   │   ├── dashboard/
│   │   │   └── index.vue
│   │   ├── users/
│   │   │   └── index.vue
│   │   ├── roles/
│   │   │   └── index.vue
│   │   ├── admins/
│   │   │   └── index.vue
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
│   │       ├── config.vue
│   │       ├── logs.vue
│   │       ├── backups.vue
│   │       └── event-logs.vue
│   ├── App.vue
│   └── main.ts
├── index.html
├── package.json
├── tailwind.config.js
├── tsconfig.json
├── tsconfig.app.json
├── tsconfig.node.json
├── vite.config.ts
├── wrangler.toml             # Cloudflare Workers 部署配置
├── Dockerfile                # Nginx 备用部署
├── nginx.conf                # Nginx 配置
└── .env
```

### 3.2 文件说明

| 目录 | 说明 |
|------|------|
| `api/` | 按模块组织API接口，统一封装axios |
| `components/common/` | 纯Tailwind CSS实现的通用组件 |
| `components/layout/` | 布局组件（侧边栏、头部、主内容区） |
| `composables/` | Vue 3组合式函数（操作锁等） |
| `router/` | 路由配置，支持权限校验 |
| `stores/` | Pinia状态管理 |
| `types/` | TypeScript类型定义 |
| `utils/` | 工具函数（日期格式化等） |
| `views/` | 页面视图，按功能模块分组 |

## 四、技术栈详情

### 4.1 依赖列表

```json
{
  "dependencies": {
    "vue": "^3.5.40",
    "vue-router": "^4.6.4",
    "pinia": "^4.0.2",
    "axios": "^1.19.0",
    "dayjs": "^1.11.21",
    "@heroicons/vue": "^2.2.0"
  },
  "devDependencies": {
    "vite": "^8.2.0",
    "typescript": "~6.0.2",
    "vue-tsc": "^3.3.8",
    "tailwindcss": "^3.4.19",
    "postcss": "^8.5.26",
    "autoprefixer": "^10.5.4",
    "@vitejs/plugin-vue": "^6.0.8",
    "@cloudflare/workers-types": "^5.20260810.0"
  }
}
```

### 4.2 版本说明

| 分类 | 技术 | 版本 |
|------|------|------|
| 构建工具 | Vite | ^8.2.0 |
| 前端框架 | Vue 3 | ^3.5.40 |
| 类型检查 | TypeScript | ~6.0.2 |
| 路由 | Vue Router | ^4.6.4 |
| 状态管理 | Pinia | ^4.0.2 |
| 样式 | Tailwind CSS | ^3.4.19 |
| HTTP请求 | Axios | ^1.19.0 |
| 图标 | Heroicons | ^2.2.0 |
| 日期处理 | Day.js | ^1.11.21 |

## 五、页面功能设计

### 5.1 登录页 `/login`

**功能**：
- 账号密码登录
- 记住登录状态
- 登录失败错误提示

**布局**：
```
┌─────────────────────────────────────────┐
│           Tennis Diary Admin            │
├─────────────────────────────────────────┤
│  ┌─────────────────────────────────┐   │
│  │  [用户名] ___________________   │   │
│  │  [密码]   ___________________   │   │
│  │  [✓ 记住我]                     │   │
│  │  [登录按钮]                     │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

### 5.2 仪表盘 `/dashboard`

**功能**：
- 数据概览卡片（用户数、日记数、装备数、打卡数）
- 系统状态（数据库、磁盘、运行时长）
- 数据库信息（大小、各表数据量）

### 5.3 用户管理 `/users`

**功能**：
- 用户列表（分页）
- 查看用户详情

**列表字段**：
| 字段 | 说明 |
|------|------|
| ID | 用户ID |
| 昵称 | 用户昵称 |
| 头像 | 用户头像缩略图 |
| 性别 | 性别 |
| 注册时间 | 创建时间 |
| 操作 | 查看详情 |

### 5.4 角色管理 `/roles`

**功能**：
- 角色列表
- 创建角色
- 编辑角色（名称、描述、权限）
- 删除角色（系统角色不可删除）

### 5.5 管理员管理 `/admins`

**功能**：
- 管理员列表
- 创建管理员
- 编辑管理员（昵称、角色）
- 启用/禁用
- 重置密码
- 删除管理员

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
- 系统状态（状态、版本、运行时长）
- 资源使用（数据库、磁盘）
- AI 网关状态（AI评分、ffmpeg、MediaPipe、姿态模型）
- AI 连接测试

#### 系统配置 `/system/config`
- 配置项概览（总数、可编辑、已覆盖）
- AI 服务商管理（直选/自定义）
- 分类配置卡片（按类别分组）
- 配置项编辑/恢复默认

#### 日志查看 `/system/logs`
- 日志列表（支持按级别/关键字筛选）
- 分页加载
- 实时刷新

#### 备份管理 `/system/backups`
- 备份列表
- 创建备份
- 恢复备份
- 删除备份
- 上传备份

#### 事件日志 `/system/event-logs`
- 事件日志列表
- 分页加载

## 六、路由设计

### 6.1 路由配置

```typescript
// router/routes.ts
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
```

## 七、状态管理设计

### 7.1 认证状态

```typescript
// stores/auth.ts
export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('admin_token'))
  const admin = ref<AdminInfo | null>(null)
  
  const isLoggedIn = computed(() => !!token.value)
  const permissions = computed(() => admin.value?.role?.permissions || [])
  
  async function doLogin(username: string, password: string) {
    const res = await loginApi({ username, password })
    token.value = res.access_token
    localStorage.setItem('admin_token', res.access_token)
    await fetchAdminInfo()
    return res
  }
  
  async function fetchAdminInfo() {
    if (!token.value) return
    try {
      admin.value = await getAdminInfo()
    } catch {
      removeToken()
    }
  }
  
  function hasPermission(perm: string) {
    if (admin.value?.role?.code === 'superadmin') return true
    return permissions.value.includes(perm)
  }
  
  function removeToken() {
    token.value = null
    admin.value = null
    localStorage.removeItem('admin_token')
  }
  
  return { token, admin, isLoggedIn, permissions, doLogin, fetchAdminInfo, hasPermission, removeToken }
})
```

## 八、API接口封装

### 8.1 Axios实例

```typescript
// api/index.ts
const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 15000
})

// 请求拦截器：添加 X-Auth-Token
request.interceptors.request.use(config => {
  const authStore = useAuthStore()
  if (authStore.token) {
    config.headers['X-Auth-Token'] = authStore.token
  }
  setGlobalLoading(true)
  return config
})

// 响应拦截器：统一错误处理
request.interceptors.response.use(
  response => {
    setGlobalLoading(false)
    const res = response.data as ApiResponse<any>
    if (res.code !== 0) {
      const toast = useToastStore()
      toast.error(res.message || '操作失败')
      return Promise.reject(new Error(res.message))
    }
    return res.data
  },
  error => {
    setGlobalLoading(false)
    // 401 自动跳转登录页
    if (status === 401) {
      authStore.removeToken()
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)
```

## 九、环境变量配置

### 9.1 环境变量文件

```bash
# .env
VITE_APP_TITLE=Tennis Diary Admin
VITE_APP_VERSION=1.0.0
VITE_API_BASE_URL=https://your-api-server.com
```

### 9.2 类型声明

```typescript
// env.d.ts
interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string
  readonly VITE_APP_TITLE: string
  readonly VITE_APP_VERSION: string
}
```

## 十、部署配置

### 10.1 Cloudflare Workers 部署（推荐）

```toml
# wrangler.toml
name = "tennis-diary-admin"
compatibility_date = "2024-01-01"

[assets]
directory = "./dist"
not_found_handling = "single-page-application"
```

**部署命令**：
```bash
cd admin
pnpm build
pnpm cf:deploy
```

或手动部署：
```bash
pnpm build && npx wrangler deploy
```

### 10.2 Nginx 部署（备用）

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
    gzip_min_length 1000;

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

## 十一、验收标准

### 11.1 功能验收

| 功能 | 验收标准 |
|------|---------|
| 登录 | 支持账号密码登录 |
| 仪表盘 | 正确显示数据概览和系统状态 |
| 用户管理 | 列表分页、查看详情正常 |
| 角色管理 | CRUD操作正常，系统角色保护 |
| 管理员管理 | 创建/编辑/删除/重置密码正常 |
| 数据管理 | 日记/装备/体重/分析列表正常 |
| 系统监控 | 健康检查/日志/备份/配置功能正常 |
| 权限控制 | 无权限菜单隐藏，接口拦截正确 |
| 部署 | Cloudflare Workers SPA路由正常 |

### 11.2 代码质量验收

| 检查项 | 标准 |
|--------|------|
| TypeScript | 无类型错误 |
| 构建 | `pnpm build` 成功 |
| 部署 | SPA子路径路由正常 |

## 十二、实施步骤

### Phase Admin-1: 项目初始化（1-2天）

1. 创建admin目录
2. 初始化Vite + Vue 3 + TypeScript项目
3. 配置Tailwind CSS
4. 配置Vue Router和Pinia
5. 创建基础目录结构

### Phase Admin-2: 布局与登录（2-3天）

1. 实现MainLayout布局
2. 实现Sidebar侧边栏
3. 实现Header头部
4. 实现登录页（账号密码登录）
5. 实现路由守卫
6. 实现Toast/Loading组件

### Phase Admin-3: 仪表盘（1-2天）

1. 实现仪表盘页面
2. 对接系统统计API
3. 显示系统状态和数据库信息

### Phase Admin-4: 管理功能（3-4天）

1. 实现用户管理页面
2. 实现角色管理页面
3. 实现管理员管理页面
4. 实现通用组件（Table、Pagination、Modal）

### Phase Admin-5: 数据管理（2-3天）

1. 实现日记管理页面
2. 实现装备管理页面
3. 实现体重管理页面
4. 实现分析报告页面

### Phase Admin-6: 系统监控（3-4天）

1. 实现健康检查页面（含AI网关状态）
2. 实现系统配置页面（服务商管理、配置编辑）
3. 实现日志查看页面
4. 实现备份管理页面
5. 实现事件日志页面

### Phase Admin-7: 测试与部署（2-3天）

1. 配置Cloudflare Workers部署
2. 编写CI/CD流程
3. 优化和修复
4. 文档完善

## 十三、时间估算

| 阶段 | 内容 | 预计时间 |
|------|------|---------|
| Phase Admin-1 | 项目初始化 + 路由 + 布局 | 1-2天 |
| Phase Admin-2 | 登录页 + 组件 | 2-3天 |
| Phase Admin-3 | 仪表盘 | 1-2天 |
| Phase Admin-4 | 用户/角色/管理员管理 | 3-4天 |
| Phase Admin-5 | 数据管理（日记/装备/体重等） | 2-3天 |
| Phase Admin-6 | 系统监控（健康/配置/日志/备份） | 3-4天 |
| Phase Admin-7 | 测试 + 部署配置 | 2-3天 |
| **总计** | | **14-21天** |
