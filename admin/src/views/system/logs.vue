<template>
  <div class="p-6">
    <h1 class="text-2xl font-bold text-gray-800 mb-6">日志查看</h1>

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
            <option value="DEBUG">DEBUG</option>
            <option value="INFO">INFO</option>
            <option value="WARNING">WARNING</option>
            <option value="ERROR">ERROR</option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">关键字</label>
          <input
            v-model="filters.keyword"
            type="text"
            class="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-olive-500"
            placeholder="搜索关键字"
          />
        </div>
        <div class="flex items-end gap-2">
          <button
            @click="fetchLogs(true)"
            class="px-4 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200"
          >
            刷新
          </button>
          <button
            @click="fetchLogs(true)"
            class="px-4 py-2 bg-olive-600 text-white rounded-md hover:bg-olive-700"
          >
            查询
          </button>
        </div>
      </div>
    </div>

    <!-- 日志列表 -->
    <div class="bg-white rounded-lg shadow-md overflow-hidden">
      <div class="p-4 border-b flex items-center justify-between">
        <span class="text-sm text-gray-600">已加载 {{ logs.length }} 条日志</span>
        <button
          @click="loadMore"
          :disabled="!hasMore"
          class="px-3 py-1 text-sm bg-olive-50 text-olive-700 rounded-md hover:bg-olive-100 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          加载更早
        </button>
      </div>
      <div class="max-h-[600px] overflow-y-auto">
        <div
          v-for="(log, index) in logs"
          :key="index"
          class="px-4 py-2 border-b last:border-b-0 font-mono text-sm hover:bg-gray-50"
        >
          {{ log }}
        </div>
        <div v-if="logs.length === 0" class="p-12 text-center text-gray-500">
          暂无日志
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { getLogs } from '@/api/system'

const PAGE_SIZE = 500

const logs = ref<string[]>([])
const hasMore = ref(false)
const filters = reactive({
  level: '',
  keyword: ''
})
// 若翻过页，暂停自动刷新，避免打断查看历史
let viewedOlder = false

const fetchLogs = async (reset = true) => {
  try {
    const data = await getLogs({
      level: filters.level || undefined,
      keyword: filters.keyword || undefined,
      limit: PAGE_SIZE,
      offset: reset ? 0 : logs.value.length // 续载则跳过已加载的匹配数
    })
    logs.value = reset ? data.logs : [...logs.value, ...data.logs]
    hasMore.value = data.has_more
    if (reset) viewedOlder = false
  } catch (e) {
    console.error('Failed to fetch logs:', e)
  }
}

const loadMore = () => {
  viewedOlder = true
  fetchLogs(false)
}

let timer: ReturnType<typeof setInterval> | undefined
onMounted(() => {
  fetchLogs()
  // 仅停留在最新页时自动刷新，避免打断历史查看
  timer = setInterval(() => !viewedOlder && fetchLogs(), 10_000)
})
onUnmounted(() => clearInterval(timer))
</script>
