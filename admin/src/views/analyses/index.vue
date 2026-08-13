<template>
  <div class="p-6">
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-2xl font-bold text-gray-800">分析报告</h1>
    </div>

    <Table :columns="columns" :data="analyses">
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
          class="h-10 w-16 object-cover rounded"
          alt="封面"
        />
        <span v-else class="text-gray-400">--</span>
      </template>

      <template #cell-score="{ value }">
        <span v-if="value !== null && value !== undefined" class="text-olive-600 font-medium">{{ value }}</span>
        <span v-else class="text-gray-400">--</span>
      </template>

      <template #cell-created_at="{ value }">
        {{ formatDate(value) }}
      </template>

      <template #actions="{ row }">
        <button
          @click="viewAnalysis(row)"
          class="text-olive-600 hover:text-olive-800 mr-3"
        >
          查看
        </button>
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

const columns = [
  { key: 'id', title: 'ID' },
  { key: 'user', title: '用户' },
  { key: 'date', title: '日期' },
  { key: 'kind', title: '类型' },
  { key: 'mode', title: '模式' },
  { key: 'thumb', title: '封面' },
  { key: 'score', title: '评分' },
  { key: 'created_at', title: '创建时间' }
]

const analyses = ref<Analysis[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const showDetail = ref(false)
const selectedAnalysis = ref<Analysis | null>(null)
const detail = ref<Analysis | null>(null)

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

// 图片路径兼容：相对路径走静态文件服务；http(s):// 绝对 URL 原样返回
const fileUrl = (p?: string | null): string => {
  if (!p) return ''
  if (p.startsWith('http://') || p.startsWith('https://') || p.startsWith('data:')) return p
  return `/api/admin/system/files/${p}`
}

const formatDate = (date: string) => {
  if (!date) return '--'
  return new Date(date).toLocaleDateString('zh-CN')
}

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
    const res = await getAnalyses({ offset, limit: pageSize.value })
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