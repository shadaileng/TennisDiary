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
  // 模拟登录成功
  authStore.setToken('mock_token')
  router.push('/dashboard')
}
</script>
