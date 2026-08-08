> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 48-Admin-1 |
> | 文档版本 | v1.0.0 |
> | 文档状态 | ✅ 已完成 |
> | 最后更新 | 2026-08-08 |
> | 对应功能/内容 | 后台管理前端项目初始化（Vite + Vue 3 + TypeScript + Tailwind CSS） |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-08-08 | v1.0.0 | 初版 |
>
> **关联文档**：[Phase Admin 后台管理前端总纲](./47-Admin-后台管理前端.md)

# Phase Admin-1：项目初始化

## 一、目标

创建 admin 目录，初始化 Vite + Vue 3 + TypeScript 项目，配置 Tailwind CSS、Vue Router、Pinia，建立基础目录结构和通用组件。

## 二、前置条件

- Phase B2 已完成（后台管理API全部就绪）
- Node.js ≥ 22.12

## 三、详细执行步骤

### 3.1 创建 admin 目录并初始化项目

```bash
cd D:\workspace\TennisDiary
npm create vite@latest admin -- --template vue-ts
cd admin
npm install
```

### 3.2 安装依赖

```bash
# 核心依赖
npm install vue-router@4 pinia axios dayjs @heroicons/vue

# 开发依赖
npm install -D tailwindcss@3 postcss autoprefixer @tailwindcss/forms
npx tailwindcss init -p
```

### 3.3 配置 Tailwind CSS

**tailwind.config.js**：
```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        olive: {
          50: '#f8f7f4',
          100: '#f0ede6',
          200: '#e2dccb',
          300: '#cfc5a8',
          400: '#bba985',
          500: '#a8906a',
          600: '#9b7e5e',
          700: '#81664e',
          800: '#6a5443',
          900: '#574639',
          950: '#2e241d',
        },
        lime: {
          50: '#f7fce4',
          100: '#ecf8c5',
          200: '#daf196',
          300: '#c0e55e',
          400: '#a8d634',
          500: '#8bbf16',
          600: '#6b9a0e',
          700: '#51740f',
          800: '#425c13',
          900: '#394e16',
          950: '#1d2b07',
        },
      },
    },
  },
  plugins: [],
}
```

**src/styles/main.css**：
```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

### 3.4 配置 Vue Router

**src/router/index.ts**：
```typescript
import { createRouter, createWebHistory } from 'vue-router'
import routes from './routes'

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('admin_token')
  
  if (to.meta.requiresAuth && !token) {
    next({ name: 'Login', query: { redirect: to.fullPath } })
    return
  }
  
  if (to.name === 'Login' && token) {
    next({ name: 'Dashboard' })
    return
  }
  
  next()
})

export default router
```

**src/router/routes.ts**：
```typescript
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

### 3.5 配置 Pinia

**src/stores/index.ts**：
```typescript
import { createPinia } from 'pinia'

const pinia = createPinia()

export default pinia
```

**src/stores/auth.ts**：
```typescript
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('admin_token'))
  
  const isLoggedIn = computed(() => !!token.value)
  
  function setToken(newToken: string) {
    token.value = newToken
    localStorage.setItem('admin_token', newToken)
  }
  
  function removeToken() {
    token.value = null
    localStorage.removeItem('admin_token')
  }
  
  return { token, isLoggedIn, setToken, removeToken }
})
```

### 3.6 配置路径别名

**vite.config.ts**：
```typescript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
})
```

**tsconfig.json**（添加 paths）：
```json
{
  "compilerOptions": {
    "paths": {
      "@/*": ["./src/*"]
    }
  }
}
```

### 3.7 创建基础目录结构

```
admin/src/
├── api/                  # API接口
│   └── index.ts          # axios实例
├── components/           # 公共组件
│   └── layout/           # 布局组件
│       └── MainLayout.vue
├── router/               # 路由配置
│   ├── index.ts
│   └── routes.ts
├── stores/               # Pinia状态
│   ├── index.ts
│   └── auth.ts
├── styles/               # 样式
│   └── main.css
├── types/                # TypeScript类型
│   └── index.ts
├── utils/                # 工具函数
│   └── storage.ts
├── views/                # 页面视图
│   ├── login/
│   │   └── index.vue
│   └── dashboard/
│       └── index.vue
├── App.vue
└── main.ts
```

### 3.8 实现基础页面

**src/views/login/index.vue**：
```vue
<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-100">
    <div class="w-full max-w-md p-8 bg-white rounded-lg shadow-md">
      <h1 class="text-2xl font-bold text-center text-olive-700 mb-6">
        Tennis Diary Admin
      </h1>
      <form @submit.prevent="handleLogin">
        <div class="mb-4">
          <label class="block text-sm font-medium text-gray-700 mb-1">
            用户名
          </label>
          <input
            v-model="username"
            type="text"
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-olive-500"
            placeholder="请输入用户名"
          />
        </div>
        <div class="mb-6">
          <label class="block text-sm font-medium text-gray-700 mb-1">
            密码
          </label>
          <input
            v-model="password"
            type="password"
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-olive-500"
            placeholder="请输入密码"
          />
        </div>
        <button
          type="submit"
          class="w-full py-2 px-4 bg-olive-600 text-white rounded-md hover:bg-olive-700 focus:outline-none focus:ring-2 focus:ring-olive-500"
        >
          登录
        </button>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const username = ref('')
const password = ref('')

const handleLogin = async () => {
  // TODO: 对接登录API
  console.log('Login:', username.value, password.value)
}
</script>
```

**src/views/dashboard/index.vue**：
```vue
<template>
  <div class="p-6">
    <h1 class="text-2xl font-bold text-gray-800 mb-6">仪表盘</h1>
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      <div class="bg-white p-6 rounded-lg shadow-md">
        <h3 class="text-lg font-medium text-gray-600">用户总数</h3>
        <p class="text-3xl font-bold text-olive-600">--</p>
      </div>
      <div class="bg-white p-6 rounded-lg shadow-md">
        <h3 class="text-lg font-medium text-gray-600">日记总数</h3>
        <p class="text-3xl font-bold text-olive-600">--</p>
      </div>
      <div class="bg-white p-6 rounded-lg shadow-md">
        <h3 class="text-lg font-medium text-gray-600">装备总数</h3>
        <p class="text-3xl font-bold text-olive-600">--</p>
      </div>
      <div class="bg-white p-6 rounded-lg shadow-md">
        <h3 class="text-lg font-medium text-gray-600">今日打卡</h3>
        <p class="text-3xl font-bold text-olive-600">--</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
// TODO: 对接系统统计API
</script>
```

**src/components/layout/MainLayout.vue**：
```vue
<template>
  <div class="min-h-screen flex">
    <!-- 侧边栏 -->
    <aside class="w-64 bg-olive-800 text-white">
      <div class="p-4">
        <h1 class="text-xl font-bold">Tennis Diary</h1>
        <p class="text-sm text-olive-200">后台管理</p>
      </div>
      <nav class="mt-4">
        <router-link
          to="/dashboard"
          class="block px-4 py-2 hover:bg-olive-700"
        >
          仪表盘
        </router-link>
      </nav>
    </aside>
    
    <!-- 主内容区 -->
    <div class="flex-1 flex flex-col">
      <!-- 头部 -->
      <header class="h-16 bg-white border-b flex items-center justify-between px-6">
        <span class="text-gray-600">欢迎，管理员</span>
        <button
          @click="handleLogout"
          class="text-sm text-gray-600 hover:text-olive-600"
        >
          退出登录
        </button>
      </header>
      
      <!-- 内容 -->
      <main class="flex-1 bg-gray-100">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const handleLogout = () => {
  authStore.removeToken()
  router.push('/login')
}
</script>
```

**src/App.vue**：
```vue
<template>
  <router-view />
</template>

<script setup lang="ts">
</script>
```

**src/main.ts**：
```typescript
import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import pinia from './stores'
import './styles/main.css'

const app = createApp(App)
app.use(router)
app.use(pinia)
app.mount('#app')
```

### 3.9 配置环境变量

**.env**：
```
VITE_APP_TITLE=Tennis Diary Admin
VITE_APP_VERSION=1.0.0
```

**.env.development**：
```
VITE_API_BASE_URL=http://localhost:8000
```

**.env.production**：
```
VITE_API_BASE_URL=https://api.example.com
```

**src/env.d.ts**：
```typescript
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

## 四、验收标准

| 验收项 | 标准 |
|--------|------|
| 项目初始化 | `npm run dev` 启动成功 |
| Tailwind CSS | 自定义 olive/lime 颜色可用 |
| Vue Router | 路由跳转正常，未登录重定向到登录页 |
| Pinia | 状态管理正常 |
| 路径别名 | `@/` 别名可用 |
| 登录页 | 页面渲染正常 |
| 仪表盘 | 页面渲染正常 |
| 主布局 | 侧边栏+头部+内容区布局正常 |

## 五、提交规范

```bash
feat(admin): 初始化后台管理前端项目

- 创建admin目录结构
- 配置Vite + Vue 3 + TypeScript
- 配置Tailwind CSS（olive/lime主题色）
- 配置Vue Router和Pinia
- 实现基础布局组件（MainLayout）
- 实现登录页和仪表盘占位页
```