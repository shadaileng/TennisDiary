<template>
  <div class="p-6">
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-2xl font-bold text-gray-800">分析报告</h1>
    </div>

    <Table :columns="columns" :data="analyses">
      <template #cell-user="{ row }">
        {{ row.user?.nickname || '--' }}
      </template>

      <template #cell-score="{ value }">
        <span v-if="value" class="text-olive-600 font-medium">{{ value }}</span>
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
      <div v-if="selectedAnalysis" class="space-y-4">
        <div>
          <p class="text-sm text-gray-500">日期</p>
          <p>{{ selectedAnalysis.date }}</p>
        </div>
        <div>
          <p class="text-sm text-gray-500">类型</p>
          <p>{{ selectedAnalysis.kind }}</p>
        </div>
        <div v-if="selectedAnalysis.score">
          <p class="text-sm text-gray-500">评分</p>
          <p class="text-olive-600 font-medium">{{ selectedAnalysis.score }}</p>
        </div>
        <div>
          <p class="text-sm text-gray-500">报告</p>
          <p class="whitespace-pre-wrap">{{ selectedAnalysis.summary }}</p>
        </div>
      </div>
    </Modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getAnalyses, deleteAnalysis, type Analysis } from '@/api/analyses'
import Table from '@/components/common/Table.vue'
import Pagination from '@/components/common/Pagination.vue'
import Modal from '@/components/common/Modal.vue'

const columns = [
  { key: 'id', title: 'ID' },
  { key: 'user', title: '用户' },
  { key: 'date', title: '日期' },
  { key: 'kind', title: '类型' },
  { key: 'score', title: '评分' },
  { key: 'created_at', title: '创建时间' }
]

const analyses = ref<Analysis[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const showDetail = ref(false)
const selectedAnalysis = ref<Analysis | null>(null)

const formatDate = (date: string) => {
  return new Date(date).toLocaleDateString('zh-CN')
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

const viewAnalysis = (analysis: Analysis) => {
  selectedAnalysis.value = analysis
  showDetail.value = true
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
