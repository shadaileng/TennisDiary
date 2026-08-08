<template>
  <div class="p-6">
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-2xl font-bold text-gray-800">日记管理</h1>
    </div>

    <Table :columns="columns" :data="diaries">
      <template #cell-user="{ row }">
        {{ row.user?.nickname || '--' }}
      </template>

      <template #cell-type="{ value }">
        <span class="px-2 py-1 text-xs rounded-full bg-blue-100 text-blue-800">
          {{ value }}
        </span>
      </template>

      <template #cell-duration="{ value }">
        {{ value }} 分钟
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
import { getDiaries, deleteDiary, type Diary } from '@/api/diaries'
import Table from '@/components/common/Table.vue'
import Pagination from '@/components/common/Pagination.vue'

const columns = [
  { key: 'id', title: 'ID' },
  { key: 'user', title: '用户' },
  { key: 'date', title: '日期' },
  { key: 'type', title: '类型' },
  { key: 'duration', title: '时长' },
  { key: 'created_at', title: '创建时间' }
]

const diaries = ref<Diary[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)

const formatDate = (date: string) => {
  return new Date(date).toLocaleDateString('zh-CN')
}

const fetchDiaries = async () => {
  try {
    const offset = (currentPage.value - 1) * pageSize.value
    const res = await getDiaries({ offset, limit: pageSize.value })
    diaries.value = res.items
    total.value = res.total
  } catch (e) {
    console.error('Failed to fetch diaries:', e)
  }
}

const confirmDelete = async (diary: Diary) => {
  if (confirm('确定要删除这条日记吗？')) {
    try {
      await deleteDiary(diary.id)
      await fetchDiaries()
    } catch (e) {
      console.error('Failed to delete diary:', e)
    }
  }
}

onMounted(fetchDiaries)
</script>
