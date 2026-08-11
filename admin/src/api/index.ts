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
