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
