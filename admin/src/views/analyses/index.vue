<template>
  <div class="p-6">
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-2xl font-bold text-gray-800">分析报告</h1>
    </div>

    <!-- 筛选条件 -->
    <div class="bg-white rounded-lg shadow-md p-4 mb-6">
      <div class="flex flex-wrap gap-x-6 gap-y-3">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">开始日期</label>
          <input
            type="date"
            v-model="filterForm.date_from"
            class="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-olive-500"
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">结束日期</label>
          <input
            type="date"
            v-model="filterForm.date_to"
            class="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-olive-500"
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">类型</label>
          <select
            v-model="filterForm.kind"
            class="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-olive-500"
          >
            <option value="">全部</option>
            <option>综合</option>
            <option>正手</option>
            <option>反手</option>
            <option>截击</option>
            <option>发球</option>
            <option>高压</option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">模式</label>
          <select
            v-model="filterForm.mode"
            class="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-olive-500"
          >
            <option value="">全部</option>
            <option value="single">单次挥拍</option>
            <option value="full">综合分析</option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">状态</label>
          <select
            v-model="filterForm.status"
            class="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-olive-500"
          >
            <option value="">全部</option>
            <option value="processing">处理中</option>
            <option value="completed">已完成</option>
            <option value="failed">失败</option>
          </select>
        </div>
        <div class="flex items-end gap-2">
          <button
            @click="handleSearch"
            class="px-4 py-2 bg-olive-600 text-white rounded-md hover:bg-olive-700"
          >
            查询
          </button>
          <button
            @click="handleReset"
            class="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50"
          >
            重置
          </button>
        </div>
      </div>
    </div>

    <Table :columns="columns" :data="analyses" :row-clickable="true" @row-click="viewAnalysis">
      <template #cell-user="{ row }">
        {{ row.user?.nickname || '--' }}
      </template>

      <template #cell-mode="{ value }">
        <span
          v-if="value === 'single'"
          class="px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-700"
        >
          单次挥拍
        </span>
        <span
          v-else-if="value === 'full'"
          class="px-2 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-700"
        >
          综合分析
        </span>
        <span v-else class="text-gray-400">--</span>
      </template>

      <template #cell-thumb="{ row }">
        <img
          v-if="row.thumb && fileUrl(row.thumb)"
          :src="fileUrl(row.thumb)"
          class="h-8 w-12 object-cover rounded"
          alt="封面"
        />
        <span v-else class="text-gray-400">--</span>
      </template>

      <template #cell-score="{ value }">
        <span v-if="value !== null && value !== undefined" class="text-olive-600 font-medium">{{ value }}</span>
        <span v-else class="text-gray-400">--</span>
      </template>

      <template #cell-created_at="{ value }">
        {{ formatTs(value) }}
      </template>

      <template #actions="{ row }">
        <button
          @click="confirmDelete(row)"
          class="text-red-600 hover:text-red-800"
        >
          删除
        </button>
      </template>
    </Table>

    <Pagination
      :total="total"
      :page-size="pageSize"
      v-model:current-page="currentPage"
    />

    <!-- 分析详情模态框 -->
    <Modal v-model="showDetail" title="分析报告详情">
      <div v-if="detail" class="space-y-5 max-h-[70vh] overflow-y-auto pr-1">
        <!-- 头部：总分 + NTRP + kind/mode/date -->
        <div class="flex items-start justify-between">
          <div>
            <div class="flex items-baseline gap-3">
              <span class="text-4xl font-bold" :class="scoreColor(report?.score ?? detail.score ?? 0)">
                {{ report?.score ?? detail.score ?? '--' }}
              </span>
              <span
                v-if="report?.ntrp || detail.ntrp"
                class="px-2 py-0.5 rounded-full text-xs font-medium bg-gray-200 text-gray-700"
              >
                NTRP {{ report?.ntrp || detail.ntrp }}
              </span>
            </div>
            <div class="mt-2 text-sm text-gray-500">
              {{ detail.kind }} · {{ modeLabel(detail.mode) }} · {{ detail.date }}
            </div>
          </div>
          <div v-if="report?.summary || detail.summary" class="text-sm text-gray-600 max-w-[45%]">
            {{ report?.summary || detail.summary }}
          </div>
        </div>

        <!-- 六维评分条 -->
        <div v-if="report?.dimensions?.length">
          <h3 class="text-sm font-semibold text-gray-800 mb-2">六维评分</h3>
          <div class="space-y-2">
            <div v-for="dim in report.dimensions" :key="dim.name" class="flex items-center gap-3">
              <span class="w-20 text-sm text-gray-600 shrink-0">{{ dim.name }}</span>
              <div class="flex-1 bg-gray-100 rounded-full h-2.5 overflow-hidden">
                <div
                  class="h-full rounded-full"
                  :class="barColor(dim.score)"
                  :style="{ width: `${clamp(dim.score)}%` }"
                />
              </div>
              <span class="w-10 text-sm text-gray-700 text-right shrink-0">{{ dim.score }}</span>
              <span class="flex-1 text-xs text-gray-400 min-w-0">{{ dim.comment }}</span>
            </div>
          </div>
        </div>

        <!-- 节奏观察 -->
        <div v-if="report?.rhythm">
          <h3 class="text-sm font-semibold text-gray-800 mb-1">节奏观察</h3>
          <p class="text-sm text-gray-600">{{ report.rhythm }}</p>
        </div>

        <!-- 亮点 -->
        <div v-if="report?.strengths?.length">
          <h3 class="text-sm font-semibold text-gray-800 mb-1">亮点</h3>
          <ul class="space-y-1">
            <li v-for="(s, i) in report.strengths" :key="i" class="text-sm text-green-600 flex gap-2">
              <span>✓</span><span>{{ s }}</span>
            </li>
          </ul>
        </div>

        <!-- 改进建议 -->
        <div v-if="report?.improvements?.length">
          <h3 class="text-sm font-semibold text-gray-800 mb-1">改进建议</h3>
          <ul class="space-y-2">
            <li v-for="(imp, i) in report.improvements" :key="i" class="text-sm">
              <span class="text-red-600">{{ imp.issue }}</span>
              <span v-if="imp.advice" class="text-gray-500 block mt-0.5">建议：{{ imp.advice }}</span>
            </li>
          </ul>
        </div>

        <!-- 姿态测量（Step 83） -->
        <div v-if="pose?.detected">
          <h3 class="text-sm font-semibold text-gray-800 mb-2">姿态测量</h3>
          <div v-if="pose.metrics" class="grid grid-cols-3 gap-2 mb-3">
            <div class="bg-gray-50 rounded-lg p-2 text-center">
              <div class="text-lg font-bold text-olive-600">{{ Math.round(pose.metrics.elbowAngle) }}°</div>
              <div class="text-xs text-gray-500">肘角</div>
            </div>
            <div class="bg-gray-50 rounded-lg p-2 text-center">
              <div class="text-lg font-bold text-olive-600">{{ Math.round(pose.metrics.kneeAngle) }}°</div>
              <div class="text-xs text-gray-500">膝角</div>
            </div>
            <div class="bg-gray-50 rounded-lg p-2 text-center">
              <div class="text-lg font-bold text-olive-600">{{ Math.round(pose.metrics.trunkLean) }}°</div>
              <div class="text-xs text-gray-500">躯干倾斜</div>
            </div>
          </div>
          <div v-if="fileUrl(pose.skeleton_video_url)" class="mb-3">
            <video
              :src="fileUrl(pose.skeleton_video_url)"
              controls
              class="w-full max-w-md rounded border border-gray-200"
              preload="metadata"
            />
          </div>
          <div v-else-if="fileUrl(detail.thumb)" class="mb-3">
            <img
              :src="fileUrl(detail.thumb)"
              class="h-24 w-auto object-contain rounded border border-gray-200"
              alt="骨架封面"
            />
          </div>
        </div>

        <!-- 封面 / 高光帧 -->
        <div v-if="fileUrl(detail.thumb) || detail.highlights?.length">
          <h3 class="text-sm font-semibold text-gray-800 mb-2">画面</h3>
          <img
            v-if="fileUrl(detail.thumb)"
            :src="fileUrl(detail.thumb)"
            class="w-full max-h-64 object-contain rounded border border-gray-200"
            alt="封面帧"
          />
          <div v-if="detail.highlights?.length" class="flex gap-2 mt-2 flex-wrap">
            <img
              v-for="(h, i) in detail.highlights"
              :key="i"
              :src="fileUrl(h)"
              class="h-16 w-24 object-cover rounded border border-gray-200"
              :alt="`高光帧${i + 1}`"
            />
          </div>
        </div>
      </div>
    </Modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { getAnalyses, getAnalysis, deleteAnalysis, type Analysis, type AnalysisReport } from '@/api/analyses'
import Table from '@/components/common/Table.vue'
import Pagination from '@/components/common/Pagination.vue'
import Modal from '@/components/common/Modal.vue'
import { formatTs } from '@/utils/date'
import { fileUrl } from '@/utils/fileUrl'

const columns = [
  { key: 'id', title: 'ID', width: 60 },
  { key: 'user', title: '用户', width: 120 },
  { key: 'kind', title: '类型', width: 60 },
  { key: 'mode', title: '模式', width: 90 },
  { key: 'thumb', title: '封面', width: 70 },
  { key: 'score', title: '评分', width: 60 },
  { key: 'created_at', title: '创建时间', width: 170 }
]

const analyses = ref<Analysis[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const showDetail = ref(false)
const selectedAnalysis = ref<Analysis | null>(null)
const detail = ref<Analysis | null>(null)

// 筛选表单
const filterForm = ref({
  date_from: '',
  date_to: '',
  kind: '',
  mode: '',
  status: '',
})

// 查询（重置分页到第 1 页）
const handleSearch = () => {
  currentPage.value = 1
  fetchAnalyses()
}

// 重置筛选条件
const handleReset = () => {
  filterForm.value = {
    date_from: '',
    date_to: '',
    kind: '',
    mode: '',
    status: '',
  }
  currentPage.value = 1
  fetchAnalyses()
}

const report = computed<AnalysisReport | null>(() => {
  const r = detail.value?.report
  if (!r) return null
  if (typeof r === 'string') {
    try {
      return JSON.parse(r) as AnalysisReport
    } catch {
      return null
    }
  }
  return r as AnalysisReport
})

const pose = computed(() => detail.value?.pose ?? null)


const modeLabel = (mode: string) => (mode === 'single' ? '单次挥拍' : mode === 'full' ? '综合分析' : mode || '--')

const clamp = (n: number) => Math.max(0, Math.min(100, n))

const scoreColor = (score: number) => {
  if (score >= 85) return 'text-green-600'
  if (score >= 70) return 'text-olive-600'
  if (score >= 60) return 'text-yellow-600'
  return 'text-red-500'
}

const barColor = (score: number) => {
  if (score >= 85) return 'bg-green-500'
  if (score >= 70) return 'bg-olive-500'
  if (score >= 60) return 'bg-yellow-500'
  return 'bg-red-400'
}

const fetchAnalyses = async () => {
  try {
    const offset = (currentPage.value - 1) * pageSize.value
    const res = await getAnalyses({
      offset,
      limit: pageSize.value,
      ...filterForm.value,
    })
    analyses.value = res.items
    total.value = res.total
  } catch (e) {
    console.error('Failed to fetch analyses:', e)
  }
}

const viewAnalysis = async (analysis: Analysis) => {
  selectedAnalysis.value = analysis
  showDetail.value = true
  detail.value = null
  try {
    detail.value = await getAnalysis(analysis.id)
  } catch (e) {
    console.error('Failed to fetch analysis detail:', e)
  }
}

const confirmDelete = async (analysis: Analysis) => {
  if (confirm('确定要删除这条分析报告吗？')) {
    try {
      await deleteAnalysis(analysis.id)
      await fetchAnalyses()
    } catch (e) {
      console.error('Failed to delete analysis:', e)
    }
  }
}

onMounted(fetchAnalyses)
</script>