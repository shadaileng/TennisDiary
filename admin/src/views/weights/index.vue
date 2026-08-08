<template>
  <div class="p-6">
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-2xl font-bold text-gray-800">体重管理</h1>
    </div>

    <Table :columns="columns" :data="weights">
      <template #cell-user="{ row }">
        {{ row.user?.nickname || '--' }}
      </template>

      <template #cell-weight="{ value }">
        {{ value }} kg
      </template>

      <template #cell-created_at="{ value }">
        {{ formatDate(value) }}
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
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getWeights, deleteWeight, type Weight } from '@/api/weights'
import Table from '@/components/common/Table.vue'
import Pagination from '@/components/common/Pagination.vue'

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

const formatDate = (date: string) => {
  return new Date(date).toLocaleDateString('zh-CN')
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
