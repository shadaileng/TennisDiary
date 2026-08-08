<template>
  <div class="p-6">
    <h1 class="text-2xl font-bold text-gray-800 mb-6">健康检查</h1>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <!-- 系统状态 -->
      <div class="bg-white rounded-lg shadow-md p-6">
        <h2 class="text-lg font-semibold text-gray-800 mb-4">系统状态</h2>
        <div class="space-y-4">
          <div class="flex items-center justify-between">
            <span class="text-gray-600">状态</span>
            <span
              :class="health.status === 'ok' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'"
              class="px-3 py-1 rounded-full text-sm font-medium"
            >
              {{ health.status }}
            </span>
          </div>
          <div class="flex justify-between">
            <span class="text-gray-600">版本</span>
            <span class="text-gray-800">{{ health.version }}</span>
          </div>
          <div class="flex justify-between">
            <span class="text-gray-600">运行时长</span>
            <span class="text-gray-800">{{ health.uptime }}</span>
          </div>
        </div>
      </div>

      <!-- 资源使用 -->
      <div class="bg-white rounded-lg shadow-md p-6">
        <h2 class="text-lg font-semibold text-gray-800 mb-4">资源使用</h2>
        <div class="space-y-4">
          <div>
            <div class="flex justify-between mb-1">
              <span class="text-gray-600">数据库</span>
              <span :class="health.database === 'ok' ? 'text-green-600' : 'text-red-600'">
                {{ health.database }}
              </span>
            </div>
          </div>
          <div>
            <div class="flex justify-between mb-1">
              <span class="text-gray-600">磁盘使用</span>
              <span class="text-gray-800">{{ health.disk_usage }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <button
      @click="refresh"
      class="mt-6 px-4 py-2 bg-olive-600 text-white rounded-lg hover:bg-olive-700"
    >
      刷新状态
    </button>
  </div>
</template>

<script setup lang="ts">
import { reactive, onMounted } from 'vue'
import { getHealthStatus, type HealthStatus } from '@/api/system'

const health = reactive<HealthStatus>({
  status: '--',
  version: '--',
  database: '--',
  disk_usage: '--',
  uptime: '--'
})

const fetchHealth = async () => {
  try {
    const data = await getHealthStatus()
    Object.assign(health, data)
  } catch (e) {
    console.error('Failed to fetch health status:', e)
  }
}

const refresh = () => {
  fetchHealth()
}

onMounted(fetchHealth)
</script>
