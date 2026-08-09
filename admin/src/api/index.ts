import axios from 'axios'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'
import type { ApiResponse } from '@/types/api'

const request = axios.create({
  baseURL: 'http://localhost:8000',
  timeout: 15000
})

request.interceptors.request.use(config => {
  const authStore = useAuthStore()
  if (authStore.token) {
    config.headers.Authorization = `Bearer ${authStore.token}`
  }
  return config
})

request.interceptors.response.use(
  response => {
    const res = response.data as ApiResponse<any>
    if (res.code !== 0) {
      const toast = useToastStore()
      toast.error(res.message || '操作失败')
      return Promise.reject(new Error(res.message))
    }
    return res.data
  },
  error => {
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
