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
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">消息</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">页面</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">设备</th>
          </tr>
        </thead>
        <tbody class="bg-white divide-y divide-gray-200">
          <tr v-for="event in events" :key="event.id" class="hover:bg-gray-50">
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
            <td class="px-6 py-4 text-sm text-gray-900 max-w-xs truncate">
              {{ event.message }}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
              {{ event.page || '--' }}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
              {{ event.device_info?.model || '--' }}
            </td>
          </tr>
          <tr v-if="events.length === 0">
            <td colspan="6" class="px-6 py-12 text-center text-gray-500">
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
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { getEventLogs, type EventLog } from '@/api/events'
import Pagination from '@/components/common/Pagination.vue'

const events = ref<EventLog[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)

const filters = reactive({
  level: '',
  type: '',
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

const fetchEvents = async () => {
  try {
    const res = await getEventLogs({
      level: filters.level || undefined,
      type: filters.type || undefined,
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
  filters.keyword = ''
  filters.traceId = ''
  currentPage.value = 1
  fetchEvents()
}

onMounted(fetchEvents)
</script>
