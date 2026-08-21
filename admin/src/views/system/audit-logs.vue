<template>
  <div class="p-6">
    <h1 class="text-2xl font-bold text-gray-800 mb-6">审计日志</h1>

    <!-- 筛选条件 -->
    <div class="bg-white rounded-lg shadow-md p-4 mb-6">
      <div class="flex flex-wrap gap-x-6 gap-y-3">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">来源</label>
          <select
            v-model="filters.source"
            class="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-olive-500"
          >
            <option value="">全部</option>
            <option value="admin">管理端</option>
            <option value="user">用户端</option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">操作</label>
          <select
            v-model="filters.action"
            class="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-olive-500"
          >
            <option value="">全部</option>
            <option value="CREATE">CREATE</option>
            <option value="UPDATE">UPDATE</option>
            <option value="DELETE">DELETE</option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">资源类型</label>
          <select
            v-model="filters.resource_type"
            class="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-olive-500"
          >
            <option value="">全部</option>
            <option value="admin">管理员</option>
            <option value="role">角色</option>
            <option value="diary">日记</option>
            <option value="gear">装备</option>
            <option value="weight">体重</option>
            <option value="checkin">打卡</option>
            <option value="analysis">分析报告</option>
            <option value="post">发布</option>
            <option value="user">用户</option>
            <option value="config">配置</option>
            <option value="ai_provider">AI服务商</option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">开始日期</label>
          <input
            v-model="filters.start_date"
            type="datetime-local"
            class="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-olive-500"
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">结束日期</label>
          <input
            v-model="filters.end_date"
            type="datetime-local"
            class="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-olive-500"
          />
        </div>
        <div class="flex items-end gap-2">
          <button
            @click="fetchLogs"
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

    <!-- 日志列表 -->
    <div class="bg-white rounded-lg shadow-md overflow-hidden">
      <div class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-200">
          <thead class="bg-gray-50">
            <tr>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase whitespace-nowrap">时间</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase whitespace-nowrap">来源</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase whitespace-nowrap">操作者</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase whitespace-nowrap">操作</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase whitespace-nowrap">资源类型</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase whitespace-nowrap">资源ID</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase whitespace-nowrap">路由</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase whitespace-nowrap">结果</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase whitespace-nowrap">耗时</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase whitespace-nowrap">IP</th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-200">
            <tr
              v-for="log in logs"
              :key="log.id"
              class="hover:bg-gray-50 cursor-pointer"
              @click="selectedLog = log"
            >
              <td class="px-4 py-4 whitespace-nowrap text-sm text-gray-500">
                {{ formatIso(log.created_at) }}
              </td>
              <td class="px-4 py-4 whitespace-nowrap">
                <span
                  class="px-2 py-1 text-xs rounded-full font-medium"
                  :class="log.source === 'admin' ? 'bg-blue-100 text-blue-800' : 'bg-green-100 text-green-800'"
                >
                  {{ log.source === 'admin' ? '管理端' : '用户端' }}
                </span>
              </td>
              <td class="px-4 py-4 whitespace-nowrap text-sm text-gray-900">
                {{ log.admin_username || log.user_nickname || '--' }}
              </td>
              <td class="px-4 py-4 whitespace-nowrap">
                <span
                  class="px-2 py-1 text-xs rounded-full font-medium"
                  :class="actionClass(log.action)"
                >
                  {{ log.action }}
                </span>
              </td>
              <td class="px-4 py-4 whitespace-nowrap text-sm text-gray-900">
                {{ log.resource_type }}
              </td>
              <td class="px-4 py-4 whitespace-nowrap text-sm text-gray-500">
                {{ log.resource_id || '--' }}
              </td>
              <td class="px-4 py-4 whitespace-nowrap text-sm text-gray-500 font-mono">
                {{ log.request_method }} {{ log.request_path }}
              </td>
              <td class="px-4 py-4 whitespace-nowrap">
                <span
                  class="px-2 py-1 text-xs rounded-full font-medium"
                  :class="log.response_success ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'"
                >
                  {{ log.response_success ? '成功' : '失败' }}
                </span>
              </td>
              <td class="px-4 py-4 whitespace-nowrap text-sm text-gray-500">
                {{ log.duration_ms.toFixed(0) }}ms
              </td>
              <td class="px-4 py-4 whitespace-nowrap text-sm text-gray-500">
                {{ log.ip_address }}
              </td>
            </tr>
            <tr v-if="logs.length === 0">
              <td colspan="10" class="px-4 py-12 text-center text-gray-500">
                暂无审计日志
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 分页 -->
    <Pagination
      v-if="total > 0"
      :total="total"
      :page-size="pageSize"
      v-model:current-page="currentPage"
      @update:current-page="fetchLogs"
    />

    <!-- 详情弹窗 -->
    <div
      v-if="selectedLog"
      class="fixed inset-0 z-50 flex items-center justify-center"
    >
      <div
        class="absolute inset-0 bg-black/50"
        @click="selectedLog = null"
      />
      <div class="relative bg-white rounded-lg shadow-xl w-full max-w-2xl mx-4 max-h-[90vh] overflow-hidden flex flex-col">
        <!-- 弹窗头部 -->
        <div class="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 class="text-lg font-semibold text-gray-800">审计详情</h2>
          <button
            @click="selectedLog = null"
            class="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <!-- 弹窗内容 -->
        <div class="flex-1 overflow-y-auto px-6 py-4">
          <div class="grid grid-cols-2 gap-4 mb-6">
            <div>
              <span class="text-sm font-medium text-gray-500">时间</span>
              <p class="mt-1 text-sm text-gray-900">{{ formatIso(selectedLog.created_at) }}</p>
            </div>
            <div>
              <span class="text-sm font-medium text-gray-500">来源</span>
              <p class="mt-1 text-sm text-gray-900">{{ selectedLog.source === 'admin' ? '管理端' : '用户端' }}</p>
            </div>
            <div>
              <span class="text-sm font-medium text-gray-500">操作者</span>
              <p class="mt-1 text-sm text-gray-900">{{ selectedLog.admin_username || selectedLog.user_nickname || '--' }}</p>
            </div>
            <div>
              <span class="text-sm font-medium text-gray-500">操作</span>
              <p class="mt-1">
                <span
                  class="px-2 py-1 text-xs rounded-full font-medium"
                  :class="actionClass(selectedLog.action)"
                >
                  {{ selectedLog.action }}
                </span>
              </p>
            </div>
            <div>
              <span class="text-sm font-medium text-gray-500">资源类型</span>
              <p class="mt-1 text-sm text-gray-900">{{ selectedLog.resource_type }}</p>
            </div>
            <div>
              <span class="text-sm font-medium text-gray-500">资源ID</span>
              <p class="mt-1 text-sm text-gray-900 font-mono">{{ selectedLog.resource_id || '--' }}</p>
            </div>
            <div>
              <span class="text-sm font-medium text-gray-500">路由</span>
              <p class="mt-1 text-sm text-gray-900 font-mono">{{ selectedLog.request_method }} {{ selectedLog.request_path }}</p>
            </div>
            <div>
              <span class="text-sm font-medium text-gray-500">结果</span>
              <p class="mt-1">
                <span
                  class="px-2 py-1 text-xs rounded-full font-medium"
                  :class="selectedLog.response_success ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'"
                >
                  {{ selectedLog.response_success ? '成功' : '失败' }} ({{ selectedLog.response_code }})
                </span>
              </p>
            </div>
            <div>
              <span class="text-sm font-medium text-gray-500">耗时</span>
              <p class="mt-1 text-sm text-gray-900">{{ selectedLog.duration_ms.toFixed(1) }}ms</p>
            </div>
            <div>
              <span class="text-sm font-medium text-gray-500">IP地址</span>
              <p class="mt-1 text-sm text-gray-900 font-mono">{{ selectedLog.ip_address }}</p>
            </div>
            <div>
              <span class="text-sm font-medium text-gray-500">User-Agent</span>
              <p class="mt-1 text-sm text-gray-900 break-all">{{ selectedLog.user_agent || '--' }}</p>
            </div>
          </div>

          <!-- 请求体 -->
          <div v-if="selectedLog.request_body" class="mb-4">
            <span class="text-sm font-medium text-gray-500">请求体</span>
            <pre class="mt-1 text-xs text-gray-700 bg-gray-50 rounded px-3 py-2 overflow-x-auto whitespace-pre-wrap break-words">{{ formatJson(selectedLog.request_body) }}</pre>
          </div>

          <!-- 响应信息 -->
          <div class="mb-4">
            <span class="text-sm font-medium text-gray-500">响应信息</span>
            <p class="mt-1 text-sm text-gray-900 bg-gray-50 rounded px-3 py-2">{{ selectedLog.response_message || '--' }}</p>
          </div>
        </div>

        <!-- 弹窗底部 -->
        <div class="flex justify-end px-6 py-4 border-t border-gray-200 bg-gray-50">
          <button
            @click="selectedLog = null"
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
import { getAuditLogs, type AuditLog } from '@/api/audit-logs'
import Pagination from '@/components/common/Pagination.vue'
import { formatIso } from '@/utils/date'

const logs = ref<AuditLog[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const selectedLog = ref<AuditLog | null>(null)

const filters = reactive({
  source: '',
  action: '',
  resource_type: '',
  start_date: '',
  end_date: '',
})

const actionClass = (action: string): string => {
  const map: Record<string, string> = {
    CREATE: 'bg-green-100 text-green-800',
    UPDATE: 'bg-yellow-100 text-yellow-800',
    DELETE: 'bg-red-100 text-red-800',
  }
  return map[action] || 'bg-gray-100 text-gray-800'
}

const formatJson = (str: string): string => {
  try {
    return JSON.stringify(JSON.parse(str), null, 2)
  } catch {
    return str
  }
}

const fetchLogs = async () => {
  try {
    const res = await getAuditLogs({
      source: filters.source || undefined,
      action: filters.action || undefined,
      resource_type: filters.resource_type || undefined,
      start_date: filters.start_date ? new Date(filters.start_date).toISOString() : undefined,
      end_date: filters.end_date ? new Date(filters.end_date).toISOString() : undefined,
      offset: (currentPage.value - 1) * pageSize.value,
      limit: pageSize.value,
    })
    logs.value = res.items
    total.value = res.total
  } catch (e) {
    console.error('Failed to fetch audit logs:', e)
  }
}

const resetFilters = () => {
  filters.source = ''
  filters.action = ''
  filters.resource_type = ''
  filters.start_date = ''
  filters.end_date = ''
  currentPage.value = 1
  fetchLogs()
}

onMounted(fetchLogs)
</script>
