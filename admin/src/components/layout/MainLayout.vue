<template>
  <div class="min-h-screen flex">
    <!-- 侧边栏 -->
    <Sidebar />

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
import Sidebar from './Sidebar.vue'
import Header from './Header.vue'

const authStore = useAuthStore()

onMounted(async () => {
  if (authStore.token) {
    await authStore.fetchAdminInfo()
  }
})
</script>
