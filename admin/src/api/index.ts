import axios from 'axios'
import { useAuthStore } from '@/stores/auth'
import type { ApiResponse } from '@/types/api'

const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
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
      return Promise.reject(new Error(res.message))
    }
    return res.data
  },
  error => {
    const status = error.response?.status
    const message = error.response?.data?.detail || error.response?.data?.message || '请求失败'

    if (status === 401) {
      const authStore = useAuthStore()
      authStore.removeToken()
      window.location.href = '/login'
    }

    return Promise.reject(new Error(message))
  }
)

export default request
