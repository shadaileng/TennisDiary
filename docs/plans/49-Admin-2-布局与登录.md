> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 49-Admin-2 |
> | 文档版本 | v2.0.0 |
> | 文档状态 | ✅ 已完成 |
> | 最后更新 | 2026-08-21 |
> | 对应功能/内容 | 后台管理前端布局与登录（MainLayout/Sidebar/Header/登录页） |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-08-08 | v1.0.0 | 初版 |
> | 2026-08-21 | v2.0.0 | 根据实际代码更新：X-Auth-Token、Toast/Loading组件 |
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
import { useToastStore } from '@/stores/toast'
import { useAppStore } from '@/stores/app'
import type { ApiResponse } from '@/types/api'

const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 15000
})

// 请求计数器：用于并发场景下正确关闭全局 loading
let pendingCount = 0

const setGlobalLoading = (loading: boolean) => {
  const appStore = useAppStore()
  if (loading) {
    pendingCount++
    appStore.setLoading(true)
  } else {
    pendingCount = Math.max(0, pendingCount - 1)
    if (pendingCount === 0) {
      appStore.setLoading(false)
    }
  }
}

request.interceptors.request.use(config => {
  const authStore = useAuthStore()
  if (authStore.token) {
    config.headers['X-Auth-Token'] = authStore.token
  }
  setGlobalLoading(true)
  return config
})

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
    const status = error.response?.status
    const message = error.response?.data?.detail || error.response?.data?.message || '请求失败'
    const toast = useToastStore()
    const isLoginPage = window.location.pathname.startsWith(`${import.meta.env.VITE_ADMIN_BASE || ''}/login`)

    if (status === 401 && !isLoginPage) {
      const authStore = useAuthStore()
      authStore.removeToken()
      toast.warning('登录已过期，请重新登录')
      window.location.href = `${import.meta.env.VITE_ADMIN_BASE || ''}/login`
    } else if (status === 401) {
      toast.error(message || '用户名或密码错误')
    } else {
      toast.error(message)
    }

    return Promise.reject(error)
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
      <template v-for="item in menuItems" :key="item.path">
        <!-- 有子菜单的项 -->
        <div v-if="item.children && item.children.length">
          <button
            @click="toggle(item.path)"
            class="w-full flex items-center px-4 py-3 hover:bg-olive-700 transition-colors"
            :class="{ 'bg-olive-700': isActive(item.path) }"
          >
            <component :is="item.icon" class="w-5 h-5 mr-3" />
            <span class="flex-1 text-left">{{ item.title }}</span>
          </button>
          <div v-show="openMenus.includes(item.path)" class="bg-olive-900">
            <router-link
              v-for="child in item.children"
              :key="child.path"
              :to="child.path"
              class="block px-4 py-2 pl-12 text-sm text-olive-200 hover:text-white hover:bg-olive-700 transition-colors"
              :class="{ 'text-white bg-olive-700': isActive(child.path) }"
            >
              {{ child.title }}
            </router-link>
          </div>
        </div>
        <!-- 普通菜单项 -->
        <router-link
          v-else
          :to="item.path"
          class="flex items-center px-4 py-3 hover:bg-olive-700 transition-colors"
          :class="{ 'bg-olive-700': isActive(item.path) }"
        >
          <component :is="item.icon" class="w-5 h-5 mr-3" />
          <span>{{ item.title }}</span>
        </router-link>
      </template>
    </nav>
    
    <!-- 底部信息 -->
    <div class="p-4 border-t border-olive-700">
      <p class="text-xs text-olive-300">v{{ version }}</p>
    </div>
  </aside>
</template>
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
      <!-- 用户下拉菜单 -->
      <div class="relative">
        <button
          @click="showDropdown = !showDropdown"
          class="flex items-center gap-2 p-2 hover:bg-gray-100 rounded-md"
        >
          <div class="w-8 h-8 bg-olive-200 rounded-full flex items-center justify-center">
            <span class="text-olive-700 font-medium">
              {{ authStore.admin?.nickname?.charAt(0) || 'A' }}
            </span>
          </div>
          <span class="text-sm text-gray-700 hidden sm:block">
            {{ authStore.admin?.nickname || '管理员' }}
          </span>
          <ChevronDownIcon class="w-4 h-4 text-gray-500" />
        </button>
        
        <!-- 下拉菜单 -->
        <div
          v-if="showDropdown"
          class="absolute right-0 mt-2 w-48 bg-white rounded-md shadow-lg py-1 z-50"
        >
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
```

### 3.6 实现 Toast 和 Loading 组件

**src/components/common/Toast.vue**：
```vue
<template>
  <Teleport to="body">
    <div class="fixed top-4 right-4 z-[100] flex flex-col gap-2">
      <TransitionGroup name="toast">
        <div
          v-for="toast in toasts"
          :key="toast.id"
          :class="toastClass(toast.type)"
          class="flex items-center gap-2 px-4 py-3 rounded-lg shadow-lg min-w-[280px] max-w-[420px]"
        >
          <span class="flex-1 text-sm">{{ toast.message }}</span>
          <button @click="remove(toast.id)" class="ml-2 opacity-70 hover:opacity-100">
            <XMarkIcon class="w-4 h-4" />
          </button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>
```

**src/components/common/Loading.vue**：
```vue
<template>
  <Teleport to="body">
    <div
      v-if="loading"
      class="fixed inset-0 z-[90] flex items-center justify-center bg-white/60 backdrop-blur-[1px]"
    >
      <div class="flex flex-col items-center gap-3">
        <div class="w-10 h-10 border-4 border-olive-600 border-t-transparent rounded-full animate-spin" />
        <span class="text-sm text-gray-600">加载中...</span>
      </div>
    </div>
  </Teleport>
</template>
```

## 四、验收标准

| 验收项 | 标准 |
|--------|------|
| API封装 | axios实例配置正确，X-Auth-Token拦截器正常 |
| 认证API | 登录、获取管理员信息接口封装完成 |
| 认证Store | 登录、登出、权限检查功能正常 |
| 侧边栏 | 菜单显示正确，权限控制正常，子菜单展开/收起 |
| 头部 | 用户信息显示，退出登录功能正常 |
| 面包屑 | 根据路由自动生成 |
| 登录页 | 表单验证、错误提示、登录跳转正常 |
| 路由守卫 | 未登录重定向到登录页，已登录跳转首页 |
| Toast | 操作反馈提示正常 |
| Loading | 全局加载状态正常 |

## 五、提交规范

```bash
feat(admin): 实现布局组件与登录功能

- 完善API封装（axios拦截器、X-Auth-Token、错误处理）
- 实现认证API（登录、获取管理员信息）
- 完善认证Store（登录、登出、权限检查）
- 实现侧边栏组件（菜单、权限过滤、子菜单）
- 实现头部组件（用户信息、退出登录）
- 实现面包屑组件
- 实现Toast和Loading组件
- 完善登录页（表单验证、错误提示）
```
