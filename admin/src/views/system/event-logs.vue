<template>
  <div class="p-6">
    <h1 class="text-2xl font-bold text-gray-800 mb-6">事件日志</h1>

    <!-- 筛选条件 -->
    <div class="bg-white rounded-lg shadow-md p-4 mb-6">
      <div class="flex flex-wrap gap-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">级别</label>
          <select
            v-model="filters.level"
            class="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-olive-500"
          >
            <option value="">全部</option>
            <option value="info">INFO</option>
            <option value="warn">WARN</option>
            <option value="error">ERROR</option>
            <option value="fatal">FATAL</option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">类型</label>
          <select
            v-model="filters.type"
            class="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-olive-500"
          >
            <option value="">全部</option>
            <option value="network">网络</option>
            <option value="business">业务</option>
            <option value="crash">崩溃</option>
            <option value="custom">自定义</option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">关键字</label>
          <input
            v-model="filters.keyword"
            type="text"
            class="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-olive-500"
            placeholder="搜索消息"
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">业务动作</label>
          <input
            v-model="filters.action"
            type="text"
            class="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-olive-500"
            placeholder="输入 action 过滤"
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">操作链路</label>
          <input
            v-model="filters.traceId"
            type="text"
            class="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-olive-500"
            placeholder="输入 trace_id 查看完整操作链"
          />
        </div>
        <div class="flex items-end gap-2">
          <button
            @click="fetchEvents"
            class="px-4 py-2 bg-olive-600 text-white rounded-md hover:bg-olive-700"
          >
            查询
          </button>
          <button
            @click="resetFilters"
            class="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50"
          >
            重置
          </button>
        </div>
      </div>
    </div>

    <!-- 事件列表 -->
    <div class="bg-white rounded-lg shadow-md overflow-hidden">
      <table class="min-w-full divide-y divide-gray-200">
        <thead class="bg-gray-50">
          <tr>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">时间</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">级别</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">类型</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">动作</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">消息</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">页面</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">设备</th>
          </tr>
        </thead>
        <tbody class="bg-white divide-y divide-gray-200">
          <tr
            v-for="event in events"
            :key="event.id"
            class="hover:bg-gray-50 cursor-pointer"
            @click="() => { selectedEvent = event; event.user_id && getUserInfo(event.user_id) }"
          >
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
              {{ formatClientTime(event.client_time) }}
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
              <span
                class="px-2 py-1 text-xs rounded-full font-medium"
                :class="levelClass(event.level)"
              >
                {{ event.level.toUpperCase() }}
              </span>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
              {{ event.type }}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
              {{ event.action || '--' }}
            </td>
            <td class="px-6 py-4 text-sm text-gray-900 max-w-xs truncate">
              {{ event.message }}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
              {{ event.page || '--' }}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
              {{ userDisplayName(event.user_id) }}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
              {{ event.device_info?.model || '--' }}
            </td>
          </tr>
          <tr v-if="events.length === 0">
            <td colspan="8" class="px-6 py-12 text-center text-gray-500">
              暂无事件日志
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 分页 -->
    <Pagination
      v-if="total > 0"
      :total="total"
      :page-size="pageSize"
      v-model:current-page="currentPage"
      @update:current-page="fetchEvents"
    />

    <!-- 详情弹窗 -->
    <div
      v-if="selectedEvent"
      class="fixed inset-0 z-50 flex items-center justify-center"
    >
      <div
        class="absolute inset-0 bg-black/50"
        @click="selectedEvent = null"
      />
      <div class="relative bg-white rounded-lg shadow-xl w-full max-w-2xl mx-4 max-h-[90vh] overflow-hidden flex flex-col">
        <!-- 弹窗头部 -->
        <div class="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 class="text-lg font-semibold text-gray-800">事件详情</h2>
          <button
            @click="selectedEvent = null"
            class="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <!-- 弹窗内容 -->
        <div class="flex-1 overflow-y-auto px-6 py-4">
          <!-- 基本信息 -->
          <div class="grid grid-cols-2 gap-4 mb-6">
            <div>
              <span class="text-sm font-medium text-gray-500">时间</span>
              <p class="mt-1 text-sm text-gray-900">{{ formatClientTime(selectedEvent.client_time) }}</p>
            </div>
            <div>
              <span class="text-sm font-medium text-gray-500">级别</span>
              <p class="mt-1">
                <span
                  class="px-2 py-1 text-xs rounded-full font-medium"
                  :class="levelClass(selectedEvent.level)"
                >
                  {{ selectedEvent.level.toUpperCase() }}
                </span>
              </p>
            </div>
            <div>
              <span class="text-sm font-medium text-gray-500">类型</span>
              <p class="mt-1 text-sm text-gray-900">{{ selectedEvent.type }}</p>
            </div>
            <div>
              <span class="text-sm font-medium text-gray-500">用户</span>
              <div class="mt-1 flex items-center gap-2">
                <img
                  v-if="userCache[selectedEvent.user_id!]?.avatar_url"
                  :src="resolveAvatarUrl(userCache[selectedEvent.user_id!].avatar_url)"
                  class="w-6 h-6 rounded-full object-cover"
                />
                <span class="text-sm text-gray-900">{{ userDisplayName(selectedEvent.user_id) }}</span>
                <span v-if="selectedEvent.user_id" class="text-xs text-gray-400">#{{ selectedEvent.user_id }}</span>
              </div>
            </div>
            <div>
              <span class="text-sm font-medium text-gray-500">操作链路</span>
              <p class="mt-1 text-sm text-gray-900 font-mono">{{ selectedEvent.trace_id || '--' }}</p>
            </div>
            <div>
              <span class="text-sm font-medium text-gray-500">业务动作</span>
              <p class="mt-1 text-sm text-gray-900">{{ selectedEvent.action || '--' }}</p>
            </div>
            <div>
              <span class="text-sm font-medium text-gray-500">页面</span>
              <p class="mt-1 text-sm text-gray-900">{{ selectedEvent.page || '--' }}</p>
            </div>
            <div>
              <span class="text-sm font-medium text-gray-500">上报时间</span>
              <p class="mt-1 text-sm text-gray-900">{{ formatServerTime(selectedEvent.created_at) }}</p>
            </div>
          </div>

          <!-- 消息 -->
          <div class="mb-4">
            <span class="text-sm font-medium text-gray-500">消息</span>
            <p class="mt-1 text-sm text-gray-900 bg-gray-50 rounded px-3 py-2">{{ selectedEvent.message }}</p>
          </div>

          <!-- 堆栈 -->
          <div v-if="selectedEvent.stack" class="mb-4">
            <span class="text-sm font-medium text-gray-500">堆栈信息</span>
            <pre class="mt-1 text-xs text-gray-700 bg-gray-900 text-green-400 rounded px-3 py-2 overflow-x-auto whitespace-pre-wrap break-words">{{ selectedEvent.stack }}</pre>
          </div>

          <!-- 设备信息 -->
          <div v-if="Object.keys(selectedEvent.device_info).length > 0" class="mb-4">
            <span class="text-sm font-medium text-gray-500">设备信息</span>
            <pre class="mt-1 text-xs text-gray-700 bg-gray-50 rounded px-3 py-2 overflow-x-auto whitespace-pre-wrap break-words">{{ JSON.stringify(selectedEvent.device_info, null, 2) }}</pre>
          </div>

          <!-- 扩展字段 -->
          <div v-if="Object.keys(selectedEvent.extra).length > 0" class="mb-4">
            <span class="text-sm font-medium text-gray-500">扩展字段</span>
            <pre class="mt-1 text-xs text-gray-700 bg-gray-50 rounded px-3 py-2 overflow-x-auto whitespace-pre-wrap break-words">{{ JSON.stringify(selectedEvent.extra, null, 2) }}</pre>
          </div>
        </div>

        <!-- 弹窗底部 -->
        <div class="flex justify-end px-6 py-4 border-t border-gray-200 bg-gray-50">
          <button
            @click="selectedEvent = null"
            class="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 transition-colors"
          >
            关闭
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { getEventLogs, type EventLog } from '@/api/events'
import { getUser, type User } from '@/api/users'
import Pagination from '@/components/common/Pagination.vue'

const events = ref<EventLog[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const selectedEvent = ref<EventLog | null>(null)
const userCache = ref<Record<number, User>>({})

const filters = reactive({
  level: '',
  type: '',
  action: '',
  keyword: '',
  traceId: '',
})

const levelClass = (level: string): string => {
  const map: Record<string, string> = {
    info: 'bg-blue-100 text-blue-800',
    warn: 'bg-yellow-100 text-yellow-800',
    error: 'bg-red-100 text-red-800',
    fatal: 'bg-purple-100 text-purple-800',
  }
  return map[level] || 'bg-gray-100 text-gray-800'
}

/** client_time 是毫秒时间戳，直接使用 */
const formatClientTime = (ts: number | null): string => {
  if (!ts) return '--'
  return new Date(ts).toLocaleString('zh-CN')
}

/** created_at 是秒级时间戳 */
const formatServerTime = (ts: number): string => {
  if (!ts) return '--'
  return new Date(ts * 1000).toLocaleString('zh-CN')
}

const getUserInfo = async (userId: number) => {
  if (userCache.value[userId]) return userCache.value[userId]
  try {
    const user = await getUser(userId)
    userCache.value[userId] = user
    return user
  } catch {
    return null
  }
}

const userDisplayName = (userId: number | null): string => {
  if (userId === null) return '--'
  const user = userCache.value[userId]
  if (!user) return String(userId)
  return user.nickname || String(userId)
}

const resolveAvatarUrl = (url: string): string => {
  if (url.startsWith('http')) return url
  const baseURL = import.meta.env.VITE_API_BASE_URL || ''
  const path = url.replace(/^avatars\//, 'avatar/')
  return `${baseURL}/api/upload/${path}`
}

const fetchEvents = async () => {
  try {
    const res = await getEventLogs({
      level: filters.level || undefined,
      type: filters.type || undefined,
      action: filters.action || undefined,
      keyword: filters.keyword || undefined,
      trace_id: filters.traceId || undefined,
      page: currentPage.value,
      page_size: pageSize.value,
    })
    events.value = res.items
    total.value = res.total
  } catch (e) {
    console.error('Failed to fetch event logs:', e)
  }
}

const resetFilters = () => {
  filters.level = ''
  filters.type = ''
  filters.action = ''
  filters.keyword = ''
  filters.traceId = ''
  currentPage.value = 1
  fetchEvents()
}

onMounted(fetchEvents)
</script>
