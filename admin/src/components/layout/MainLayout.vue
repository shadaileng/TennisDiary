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
