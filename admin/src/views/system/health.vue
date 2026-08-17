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

      <!-- AI 网关 -->
      <div class="bg-white rounded-lg shadow-md p-6">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-lg font-semibold text-gray-800">AI 网关</h2>
          <span
            v-if="ai.summary"
            :class="ai.summary.ok ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'"
            class="px-3 py-1 rounded-full text-xs font-medium"
          >
            {{ ai.summary.ok ? '全部就绪' : `缺失: ${ai.summary.missing.join('、')}` }}
          </span>
        </div>

        <div class="space-y-3">
          <div class="flex justify-between items-center">
            <span class="text-gray-600">AI 评分</span>
            <div class="text-right">
              <div v-if="ai.ai?.configured" class="text-gray-800">
                <span class="text-green-600 font-medium">已配置</span>
                <span class="text-gray-400 ml-2 text-xs">{{ ai.ai.key_masked }}</span>
              </div>
              <span v-else class="text-red-500">未配置</span>
            </div>
          </div>
          <div v-if="ai.ai?.model" class="flex justify-between">
            <span class="text-gray-600">模型</span>
            <span class="text-gray-800">{{ ai.ai.model }}</span>
          </div>
          <div v-if="ai.ai?.base_url" class="flex justify-between">
            <span class="text-gray-600">Base URL</span>
            <span class="text-gray-800 truncate ml-4">{{ ai.ai.base_url }}</span>
          </div>
          <div class="flex justify-between items-center">
            <span class="text-gray-600">ffmpeg</span>
            <div class="text-right">
              <span v-if="ai.ffmpeg?.available" class="text-green-600 font-medium">可用</span>
              <span v-else class="text-red-500">不可用</span>
              <div v-if="ai.ffmpeg?.version" class="text-xs text-gray-400">{{ ai.ffmpeg.version }}</div>
              <div v-if="ai.ffmpeg && !ai.ffmpeg.available" class="text-xs text-yellow-600">
                视频抽帧将不可用，请安装 ffmpeg（有 imageio-ffmpeg 兜底）
              </div>
            </div>
          </div>
          <div class="flex justify-between items-center">
            <span class="text-gray-600">MediaPipe</span>
            <span :class="ai.mediapipe?.available ? 'text-green-600 font-medium' : 'text-red-500'">
              {{ ai.mediapipe?.available ? '可用' : '不可用' }}
            </span>
          </div>
          <div class="flex justify-between items-center">
            <span class="text-gray-600">姿态模型</span>
            <div class="text-right">
              <span :class="ai.pose_model?.available ? 'text-green-600 font-medium' : 'text-red-500'">
                {{ ai.pose_model?.available ? '存在' : '缺失' }}
              </span>
              <div v-if="ai.pose_model?.path" class="text-xs text-gray-400">{{ ai.pose_model.path }}</div>
            </div>
          </div>
        </div>

        <button
          @click="testConnect"
          :disabled="testing"
          class="mt-4 px-4 py-2 text-sm bg-olive-600 text-white rounded-lg hover:bg-olive-700 disabled:opacity-50"
        >
          {{ testing ? '测试中…' : '测试 AI 连接' }}
        </button>
        <p v-if="connectMsg" class="mt-2 text-sm" :class="connectMsg.ok ? 'text-green-600' : 'text-red-500'">
          {{ connectMsg.text }}
        </p>
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
import { reactive, ref, onMounted } from 'vue'
import { getHealthStatus, getAiStatus, testAiConnect, type HealthStatus, type AiStatus } from '@/api/system'

const health = reactive<HealthStatus>({
  status: '--',
  version: '--',
  database: '--',
  disk_usage: '--',
  uptime: '--'
})

const ai = ref<AiStatus>({
  ai: { configured: false, model: '', base_url: '', key_masked: '', provider: 'custom' },
  ffmpeg: { available: false, version: '' },
  mediapipe: { available: false },
  pose_model: { available: false, path: '' },
  summary: { ok: false, missing: [] }
})
const testing = ref(false)
const connectMsg = ref<{ ok: boolean; text: string } | null>(null)

const fetchHealth = async () => {
  try {
    const data = await getHealthStatus()
    Object.assign(health, data)
  } catch (e) {
    console.error('Failed to fetch health status:', e)
  }
}

const fetchAiStatus = async () => {
  try {
    ai.value = await getAiStatus()
  } catch (e) {
    console.error('Failed to fetch AI status:', e)
  }
}

const testConnect = async () => {
  testing.value = true
  connectMsg.value = null
  try {
    const res = await testAiConnect()
    connectMsg.value = {
      ok: res.ok,
      text: res.message || (res.ok ? 'AI 连接正常' : 'AI 连接失败')
    }
  } catch (e) {
    connectMsg.value = { ok: false, text: 'AI 连接测试失败' }
  } finally {
    testing.value = false
  }
}

const refresh = () => {
  fetchHealth()
  fetchAiStatus()
}

onMounted(refresh)
</script>