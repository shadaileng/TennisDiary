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
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : '登录失败，请重试'
  } finally {
    loading.value = false
  }
}
</script>
