<template>
  <div class="p-6">
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-2xl font-bold text-gray-800">体重管理</h1>
    </div>

    <Table :columns="columns" :data="weights" :row-clickable="true" @row-click="viewWeight">
      <template #cell-user="{ row }">
        {{ row.user?.nickname || '--' }}
      </template>

      <template #cell-weight="{ value }">
        {{ value }} kg
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

    <!-- 详情弹窗 -->
    <div v-if="selectedWeight" class="fixed inset-0 z-50 flex items-center justify-center">
      <div class="absolute inset-0 bg-black/50" @click="selectedWeight = null" />
      <div class="relative bg-white rounded-lg shadow-xl w-full max-w-2xl mx-4 max-h-[90vh] overflow-hidden flex flex-col">
        <!-- 弹窗头部 -->
        <div class="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 class="text-lg font-semibold text-gray-800">体重详情</h2>
          <button
            @click="selectedWeight = null"
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
              <span class="text-sm font-medium text-gray-500">ID</span>
              <p class="mt-1 text-sm text-gray-900">{{ selectedWeight.id }}</p>
            </div>
            <div>
              <span class="text-sm font-medium text-gray-500">用户</span>
              <p class="mt-1 text-sm text-gray-900">{{ selectedWeight.user?.nickname || '--' }}</p>
            </div>
            <div>
              <span class="text-sm font-medium text-gray-500">日期</span>
              <p class="mt-1 text-sm text-gray-900">{{ selectedWeight.date || '--' }}</p>
            </div>
            <div>
              <span class="text-sm font-medium text-gray-500">体重</span>
              <p class="mt-1 text-sm text-gray-900">{{ selectedWeight.weight }} kg</p>
            </div>
            <div>
              <span class="text-sm font-medium text-gray-500">胸围</span>
              <p class="mt-1 text-sm text-gray-900">{{ selectedWeight.bust ?? '--' }}</p>
            </div>
            <div>
              <span class="text-sm font-medium text-gray-500">腰围</span>
              <p class="mt-1 text-sm text-gray-900">{{ selectedWeight.waist ?? '--' }}</p>
            </div>
            <div>
              <span class="text-sm font-medium text-gray-500">臀围</span>
              <p class="mt-1 text-sm text-gray-900">{{ selectedWeight.hip ?? '--' }}</p>
            </div>
            <div>
              <span class="text-sm font-medium text-gray-500">创建时间</span>
              <p class="mt-1 text-sm text-gray-900">{{ formatTs(selectedWeight.created_at) }}</p>
            </div>
          </div>
        </div>

        <!-- 弹窗底部 -->
        <div class="flex justify-end px-6 py-4 border-t border-gray-200 bg-gray-50">
          <button
            @click="selectedWeight = null"
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
import { ref, onMounted } from 'vue'
import { getWeights, deleteWeight, type Weight } from '@/api/weights'
import Table from '@/components/common/Table.vue'
import Pagination from '@/components/common/Pagination.vue'
import { formatTs } from '@/utils/date'

const columns = [
  { key: 'id', title: 'ID' },
  { key: 'user', title: '用户' },
  { key: 'date', title: '日期' },
  { key: 'weight', title: '体重' },
  { key: 'created_at', title: '创建时间' }
]

const weights = ref<Weight[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const selectedWeight = ref<Weight | null>(null)



const viewWeight = (weight: Weight) => {
  selectedWeight.value = weight
}

const fetchWeights = async () => {
  try {
    const offset = (currentPage.value - 1) * pageSize.value
    const res = await getWeights({ offset, limit: pageSize.value })
    weights.value = res.items
    total.value = res.total
  } catch (e) {
    console.error('Failed to fetch weights:', e)
  }
}

const confirmDelete = async (weight: Weight) => {
  if (confirm('确定要删除这条体重记录吗？')) {
    try {
      await deleteWeight(weight.id)
      await fetchWeights()
    } catch (e) {
      console.error('Failed to delete weight:', e)
    }
  }
}

onMounted(fetchWeights)
</script>
