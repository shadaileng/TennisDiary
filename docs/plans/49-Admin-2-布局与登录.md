> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 49-Admin-2 |
> | 文档版本 | v1.0.0 |
> | 文档状态 | ✅ 已完成 |
> | 最后更新 | 2026-08-08 |
> | 对应功能/内容 | 后台管理前端布局与登录（MainLayout/Sidebar/Header/登录页） |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-08-08 | v1.0.0 | 初版 |
>
> **关联文档**：[Phase Admin 后台管理前端总纲](./47-Admin-后台管理前端.md)

# Phase Admin-2：布局与登录

## 一、目标

实现完整的后台管理布局（侧边栏、头部、主内容区），实现登录页对接后端API，实现路由守卫和权限控制。

## 二、前置条件

- Phase Admin-1 已完成（项目初始化）
- Phase B2-1 已完成（管理员认证API）

## 三、详细执行步骤

### 3.1 完善 API 封装

**src/api/index.ts**：
```typescript
import axios from 'axios'
import { useAuthStore } from '@/stores/auth'

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
      authStore.removeToken()
      window.location.href = '/login'
    }
    
    return Promise.reject(new Error(message))
  }
)

export default request
```

### 3.2 实现认证 API

**src/api/auth.ts**：
```typescript
import request from './index'

export interface LoginRequest {
  username: string
  password: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
}

export interface AdminInfo {
  id: number
  username: string
  nickname: string
  role: {
    id: number
    name: string
    code: string
    permissions: string[]
  }
}

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

### 3.3 完善认证 Store

**src/stores/auth.ts**：
```typescript
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { AdminInfo } from '@/api/auth'
import { login as loginApi, getAdminInfo } from '@/api/auth'

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
    } catch (e) {
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

### 3.4 实现侧边栏组件

**src/components/layout/Sidebar.vue**：
```vue
<template>
  <aside class="w-64 bg-olive-800 text-white flex flex-col">
    <!-- Logo -->
    <div class="p-4 border-b border-olive-700">
      <h1 class="text-xl font-bold">Tennis Diary</h1>
      <p class="text-sm text-olive-200">后台管理</p>
    </div>
    
    <!-- 导航菜单 -->
    <nav class="flex-1 overflow-y-auto">
      <router-link
        v-for="item in menuItems"
        :key="item.path"
        :to="item.path"
        class="flex items-center px-4 py-3 hover:bg-olive-700 transition-colors"
        :class="{ 'bg-olive-700': isActive(item.path) }"
      >
        <component :is="item.icon" class="w-5 h-5 mr-3" />
        <span>{{ item.title }}</span>
      </router-link>
    </nav>
    
    <!-- 底部信息 -->
    <div class="p-4 border-t border-olive-700">
      <p class="text-xs text-olive-300">v{{ version }}</p>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import {
  HomeIcon,
  UsersIcon,
  ShieldCheckIcon,
  UserGroupIcon,
  DocumentTextIcon,
  WrenchIcon,
  ScaleIcon,
  ChartBarIcon,
  Cog6ToothIcon
} from '@heroicons/vue/24/outline'

const route = useRoute()
const authStore = useAuthStore()
const version = import.meta.env.VITE_APP_VERSION

const menuItems = computed(() => {
  const items = [
    { path: '/dashboard', title: '仪表盘', icon: HomeIcon, permission: '' },
    { path: '/users', title: '用户管理', icon: UsersIcon, permission: 'users:list' },
    { path: '/roles', title: '角色管理', icon: ShieldCheckIcon, permission: 'roles:list' },
    { path: '/admins', title: '管理员', icon: UserGroupIcon, permission: 'admins:list' },
    { path: '/diaries', title: '日记管理', icon: DocumentTextIcon, permission: 'diaries:list' },
    { path: '/gears', title: '装备管理', icon: WrenchIcon, permission: 'gears:list' },
    { path: '/weights', title: '体重管理', icon: ScaleIcon, permission: 'weights:list' },
    { path: '/analyses', title: '分析报告', icon: ChartBarIcon, permission: 'analyses:list' },
    { path: '/system', title: '系统监控', icon: Cog6ToothIcon, permission: '' },
  ]
  
  return items.filter(item => !item.permission || authStore.hasPermission(item.permission))
})

const isActive = (path: string) => {
  return route.path === path || route.path.startsWith(path + '/')
}
</script>
```

### 3.5 实现头部组件

**src/components/layout/Header.vue**：
```vue
<template>
  <header class="h-16 bg-white border-b flex items-center justify-between px-6">
    <!-- 左侧 -->
    <div class="flex items-center">
      <button
        @click="appStore.toggleSidebar"
        class="p-2 hover:bg-gray-100 rounded-md lg:hidden"
      >
        <Bars3Icon class="w-5 h-5" />
      </button>
      <Breadcrumb class="ml-4 hidden lg:block" />
    </div>
    
    <!-- 右侧 -->
    <div class="flex items-center gap-4">
      <!-- 通知铃铛 -->
      <button class="p-2 hover:bg-gray-100 rounded-md relative">
        <BellIcon class="w-5 h-5 text-gray-600" />
      </button>
      
      <!-- 用户下拉菜单 -->
      <div class="relative">
        <button
          @click="showDropdown = !showDropdown"
          class="flex items-center gap-2 p-2 hover:bg-gray-100 rounded-md"
        >
          <div class="w-8 h-8 bg-olive-200 rounded-full flex items-center justify-center">
            <span class="text-olive-700 font-medium">
              {{ adminStore.admin?.nickname?.charAt(0) || 'A' }}
            </span>
          </div>
          <span class="text-sm text-gray-700 hidden sm:block">
            {{ adminStore.admin?.nickname || '管理员' }}
          </span>
          <ChevronDownIcon class="w-4 h-4 text-gray-500" />
        </button>
        
        <!-- 下拉菜单 -->
        <div
          v-if="showDropdown"
          class="absolute right-0 mt-2 w-48 bg-white rounded-md shadow-lg py-1 z-50"
        >
          <router-link
            to="/profile"
            class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
            @click="showDropdown = false"
          >
            个人设置
          </router-link>
          <button
            @click="handleLogout"
            class="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
          >
            退出登录
          </button>
        </div>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useAppStore } from '@/stores/app'
import { Bars3Icon, BellIcon, ChevronDownIcon } from '@heroicons/vue/24/outline'

const router = useRouter()
const authStore = useAuthStore()
const adminStore = useAuthStore()
const appStore = useAppStore()

const showDropdown = ref(false)

const handleLogout = () => {
  authStore.removeToken()
  router.push('/login')
}
</script>
```

### 3.6 实现面包屑组件

**src/components/layout/Breadcrumb.vue**：
```vue
<template>
  <nav class="flex" aria-label="Breadcrumb">
    <ol class="flex items-center space-x-2">
      <li v-for="(item, index) in breadcrumbs" :key="index" class="flex items-center">
        <router-link
          v-if="item.path"
          :to="item.path"
          class="text-sm text-gray-500 hover:text-olive-600"
        >
          {{ item.title }}
        </router-link>
        <span v-else class="text-sm text-gray-700 font-medium">
          {{ item.title }}
        </span>
        <ChevronRightIcon
          v-if="index < breadcrumbs.length - 1"
          class="w-4 h-4 mx-2 text-gray-400"
        />
      </li>
    </ol>
  </nav>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { ChevronRightIcon } from '@heroicons/vue/24/outline'

const route = useRoute()

const breadcrumbs = computed(() => {
  const matched = route.matched.filter(item => item.meta?.title)
  return matched.map(item => ({
    title: item.meta.title as string,
    path: item.redirect ? '' : item.path
  }))
})
</script>
```

### 3.7 实现应用 Store

**src/stores/app.ts**：
```typescript
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

### 3.8 更新主布局组件

**src/components/layout/MainLayout.vue**：
```vue
<template>
  <div class="min-h-screen flex">
    <!-- 侧边栏 -->
    <Sidebar :class="{ '-ml-64': !appStore.sidebarCollapsed }" />
    
    <!-- 主内容区 -->
    <div class="flex-1 flex flex-col min-h-screen">
      <!-- 头部 -->
      <Header />
      
      <!-- 内容 -->
      <main class="flex-1 bg-gray-100 p-6">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useAppStore } from '@/stores/app'
import Sidebar from './Sidebar.vue'
import Header from './Header.vue'

const authStore = useAuthStore()
const appStore = useAppStore()

onMounted(async () => {
  if (authStore.token) {
    await authStore.fetchAdminInfo()
  }
})
</script>
```

### 3.9 完善登录页

**src/views/login/index.vue**：
```vue
<template>
  <div class="min-h-screen flex items-center justify-center bg-gradient-to-br from-olive-50 to-lime-50">
    <div class="w-full max-w-md p-8 bg-white rounded-lg shadow-lg">
      <!-- Logo -->
      <div class="text-center mb-8">
        <div class="w-16 h-16 bg-olive-600 rounded-full flex items-center justify-center mx-auto mb-4">
          <span class="text-2xl text-white font-bold">TD</span>
        </div>
        <h1 class="text-2xl font-bold text-olive-800">Tennis Diary</h1>
        <p class="text-gray-500 mt-1">后台管理系统</p>
      </div>
      
      <!-- 登录表单 -->
      <form @submit.prevent="handleLogin">
        <div class="mb-4">
          <label class="block text-sm font-medium text-gray-700 mb-1">
            用户名
          </label>
          <input
            v-model="form.username"
            type="text"
            class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-olive-500 focus:border-transparent"
            placeholder="请输入用户名"
            :disabled="loading"
          />
        </div>
        
        <div class="mb-6">
          <label class="block text-sm font-medium text-gray-700 mb-1">
            密码
          </label>
          <input
            v-model="form.password"
            type="password"
            class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-olive-500 focus:border-transparent"
            placeholder="请输入密码"
            :disabled="loading"
          />
        </div>
        
        <!-- 错误提示 -->
        <div v-if="error" class="mb-4 p-3 bg-red-50 text-red-600 text-sm rounded-lg">
          {{ error }}
        </div>
        
        <!-- 记住我 -->
        <div class="flex items-center mb-6">
          <input
            v-model="rememberMe"
            type="checkbox"
            id="remember"
            class="w-4 h-4 text-olive-600 border-gray-300 rounded focus:ring-olive-500"
          />
          <label for="remember" class="ml-2 text-sm text-gray-600">
            记住登录状态
          </label>
        </div>
        
        <button
          type="submit"
          class="w-full py-3 px-4 bg-olive-600 text-white font-medium rounded-lg hover:bg-olive-700 focus:outline-none focus:ring-2 focus:ring-olive-500 focus:ring-offset-2 transition-colors disabled:opacity-50"
          :disabled="loading"
        >
          <span v-if="loading">登录中...</span>
          <span v-else>登录</span>
        </button>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const loading = ref(false)
const error = ref('')
const rememberMe = ref(false)

const form = reactive({
  username: '',
  password: ''
})

const handleLogin = async () => {
  if (!form.username || !form.password) {
    error.value = '请输入用户名和密码'
    return
  }
  
  loading.value = true
  error.value = ''
  
  try {
    await authStore.doLogin(form.username, form.password)
    const redirect = (route.query.redirect as string) || '/dashboard'
    router.push(redirect)
  } catch (e: any) {
    error.value = e.message || '登录失败，请重试'
  } finally {
    loading.value = false
  }
}
</script>
```

## 四、验收标准

| 验收项 | 标准 |
|--------|------|
| API封装 | axios实例配置正确，请求/响应拦截器正常 |
| 认证API | 登录、获取管理员信息接口封装完成 |
| 认证Store | 登录、登出、权限检查功能正常 |
| 侧边栏 | 菜单显示正确，权限控制正常 |
| 头部 | 用户信息显示，退出登录功能正常 |
| 面包屑 | 根据路由自动生成 |
| 登录页 | 表单验证、错误提示、登录跳转正常 |
| 路由守卫 | 未登录重定向到登录页，已登录跳转首页 |

## 五、提交规范

```bash
feat(admin): 实现布局组件与登录功能

- 完善API封装（axios拦截器、错误处理）
- 实现认证API（登录、获取管理员信息）
- 完善认证Store（登录、登出、权限检查）
- 实现侧边栏组件（菜单、权限过滤）
- 实现头部组件（用户信息、退出登录）
- 实现面包屑组件
- 实现应用Store（侧边栏状态）
- 完善登录页（表单验证、错误提示）
```