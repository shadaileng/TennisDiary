<template>
  <div class="p-6">
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-2xl font-bold text-gray-800">日记管理</h1>
    </div>

    <Table :columns="columns" :data="diaries" :row-clickable="true" @row-click="viewDiary">
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
    <div v-if="selectedDiary" class="fixed inset-0 z-50 flex items-center justify-center">
      <div class="absolute inset-0 bg-black/50" @click="selectedDiary = null" />
      <div class="relative bg-white rounded-lg shadow-xl w-full max-w-2xl mx-4 max-h-[90vh] overflow-hidden flex flex-col">
        <!-- 弹窗头部 -->
        <div class="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 class="text-lg font-semibold text-gray-800">日记详情</h2>
          <button
            @click="selectedDiary = null"
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
              <p class="mt-1 text-sm text-gray-900">{{ selectedDiary.id }}</p>
            </div>
            <div>
              <span class="text-sm font-medium text-gray-500">用户</span>
              <p class="mt-1 text-sm text-gray-900">{{ selectedDiary.user?.nickname || '--' }}</p>
            </div>
            <div>
              <span class="text-sm font-medium text-gray-500">日期</span>
              <p class="mt-1 text-sm text-gray-900">{{ selectedDiary.date || '--' }}</p>
            </div>
            <div>
              <span class="text-sm font-medium text-gray-500">时间</span>
              <p class="mt-1 text-sm text-gray-900">{{ selectedDiary.time || '--' }}</p>
            </div>
            <div>
              <span class="text-sm font-medium text-gray-500">类型</span>
              <p class="mt-1">
                <span class="px-2 py-1 text-xs rounded-full bg-blue-100 text-blue-800">
                  {{ selectedDiary.type || '--' }}
                </span>
              </p>
            </div>
            <div>
              <span class="text-sm font-medium text-gray-500">时长</span>
              <p class="mt-1 text-sm text-gray-900">{{ selectedDiary.duration }} 分钟</p>
            </div>
            <div>
              <span class="text-sm font-medium text-gray-500">强度</span>
              <p class="mt-1 text-sm text-gray-900">{{ selectedDiary.intensity }}</p>
            </div>
            <div>
              <span class="text-sm font-medium text-gray-500">心情</span>
              <p class="mt-1 text-sm text-gray-900">{{ selectedDiary.mood }}</p>
            </div>
            <div>
              <span class="text-sm font-medium text-gray-500">创建时间</span>
              <p class="mt-1 text-sm text-gray-900">{{ formatTs(selectedDiary.created_at) }}</p>
            </div>
          </div>

          <div v-if="selectedDiary.costs" class="mb-4">
            <span class="text-sm font-medium text-gray-500">消耗</span>
            <pre class="mt-1 text-xs text-gray-700 bg-gray-50 rounded px-3 py-2 overflow-x-auto whitespace-pre-wrap break-words">{{ formatJson(selectedDiary.costs) }}</pre>
          </div>

          <div v-if="selectedDiary.gears" class="mb-4">
            <span class="text-sm font-medium text-gray-500">装备</span>
            <pre class="mt-1 text-xs text-gray-700 bg-gray-50 rounded px-3 py-2 overflow-x-auto whitespace-pre-wrap break-words">{{ formatJson(selectedDiary.gears) }}</pre>
          </div>

          <div v-if="selectedDiary.notes">
            <span class="text-sm font-medium text-gray-500">备注</span>
            <p class="mt-1 text-sm text-gray-900 bg-gray-50 rounded px-3 py-2 whitespace-pre-wrap">{{ selectedDiary.notes }}</p>
          </div>
        </div>

        <!-- 弹窗底部 -->
        <div class="flex justify-end px-6 py-4 border-t border-gray-200 bg-gray-50">
          <button
            @click="selectedDiary = null"
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
import { getDiaries, deleteDiary, type Diary } from '@/api/diaries'
import Table from '@/components/common/Table.vue'
import Pagination from '@/components/common/Pagination.vue'
import { formatTs } from '@/utils/date'

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
const selectedDiary = ref<Diary | null>(null)



const formatJson = (json: string): string => {
  try {
    return JSON.stringify(JSON.parse(json), null, 2)
  } catch {
    return json || '--'
  }
}

const viewDiary = (diary: Diary) => {
  selectedDiary.value = diary
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
