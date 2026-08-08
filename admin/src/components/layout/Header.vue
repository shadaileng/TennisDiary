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
import Breadcrumb from './Breadcrumb.vue'

const router = useRouter()
const authStore = useAuthStore()
const appStore = useAppStore()

const showDropdown = ref(false)

const handleLogout = () => {
  authStore.removeToken()
  router.push('/login')
}
</script>
