import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('admin_token'))
  
  const isLoggedIn = computed(() => !!token.value)
  
  function setToken(newToken: string) {
    token.value = newToken
    localStorage.setItem('admin_token', newToken)
  }
  
  function removeToken() {
    token.value = null
    localStorage.removeItem('admin_token')
  }
  
  return { token, isLoggedIn, setToken, removeToken }
})
