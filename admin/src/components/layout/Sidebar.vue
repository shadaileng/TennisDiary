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
            <svg
              class="w-4 h-4 transition-transform"
              :class="{ 'rotate-180': openMenus.includes(item.path) }"
              fill="none" stroke="currentColor" viewBox="0 0 24 24"
            >
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
            </svg>
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

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute, type RouteRecordRaw } from 'vue-router'
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
const openMenus = ref<string[]>([])

const iconMap: Record<string, any> = {
  HomeIcon, UsersIcon, ShieldCheckIcon, UserGroupIcon,
  DocumentTextIcon, WrenchIcon, ScaleIcon, ChartBarIcon, Cog6ToothIcon
}

// 从路由自动生成菜单（含子菜单展开）
const menuItems = computed(() => {
  const buildItems = (children: RouteRecordRaw[], parentPath = '/'): any[] => {
    return children
      .filter(r => r.meta?.requiresAuth !== false)
      .map(r => {
        const icon = r.meta?.icon ? iconMap[(r.meta.icon as string)] : null
        const path = `${parentPath}${r.path}`
        const childItems = r.children?.length ? buildItems(r.children, path + '/') : null
        const hasChildren = childItems && childItems.length > 0

        const perm = r.meta?.permission as string | undefined
        if (perm && !authStore.hasPermission(perm)) return null

        const item: any = {
          path,
          title: r.meta?.title || r.name?.toString() || '',
          icon,
        }
        if (hasChildren) {
          item.children = childItems.filter(Boolean)
          if (childItems.some(c => isActive(c.path))) {
            openMenus.value = [path]
          }
        }
        return item
      })
      .filter(Boolean)
  }

  const topLevel = route.matched[0]?.children || []
  return buildItems(topLevel)
})

const toggle = (path: string) => {
  openMenus.value = openMenus.value.includes(path)
    ? openMenus.value.filter(p => p !== path)
    : [path]
}

const isActive = (path: string) => {
  return route.path === path || route.path.startsWith(path + '/')
}
</script>
