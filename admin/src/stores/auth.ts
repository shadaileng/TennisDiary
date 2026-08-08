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
