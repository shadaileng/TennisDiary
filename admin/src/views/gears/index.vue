<template>
  <div class="p-6">
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-2xl font-bold text-gray-800">装备管理</h1>
    </div>

    <Table :columns="columns" :data="gears" :row-clickable="true" @row-click="viewGear">
      <template #cell-user="{ row }">
        {{ row.user?.nickname || '--' }}
      </template>

      <template #cell-price="{ value }">
        ¥{{ value?.toFixed(2) || '0.00' }}
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

    <!-- 详情弹窗 -->
    <div v-if="selectedGear" class="fixed inset-0 z-50 flex items-center justify-center">
      <div class="absolute inset-0 bg-black/50" @click="selectedGear = null" />
      <div class="relative bg-white rounded-lg shadow-xl w-full max-w-2xl mx-4 max-h-[90vh] overflow-hidden flex flex-col">
        <!-- 弹窗头部 -->
        <div class="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 class="text-lg font-semibold text-gray-800">装备详情</h2>
          <button
            @click="selectedGear = null"
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
              <p class="mt-1 text-sm text-gray-900">{{ selectedGear.id }}</p>
            </div>
            <div>
              <span class="text-sm font-medium text-gray-500">用户</span>
              <p class="mt-1 text-sm text-gray-900">{{ selectedGear.user?.nickname || '--' }}</p>
            </div>
            <div>
              <span class="text-sm font-medium text-gray-500">名称</span>
              <p class="mt-1 text-sm text-gray-900">{{ selectedGear.name || '--' }}</p>
            </div>
            <div>
              <span class="text-sm font-medium text-gray-500">种类</span>
              <p class="mt-1 text-sm text-gray-900">{{ selectedGear.category || '--' }}</p>
            </div>
            <div>
              <span class="text-sm font-medium text-gray-500">购买日期</span>
              <p class="mt-1 text-sm text-gray-900">{{ selectedGear.buy_date || '--' }}</p>
            </div>
            <div>
              <span class="text-sm font-medium text-gray-500">价格</span>
              <p class="mt-1 text-sm text-gray-900">¥{{ selectedGear.price?.toFixed(2) || '0.00' }}</p>
            </div>
            <div>
              <span class="text-sm font-medium text-gray-500">创建时间</span>
              <p class="mt-1 text-sm text-gray-900">{{ formatDate(selectedGear.created_at) }}</p>
            </div>
          </div>

          <div v-if="selectedGear.feeling" class="mb-4">
            <span class="text-sm font-medium text-gray-500">使用感受</span>
            <p class="mt-1 text-sm text-gray-900 bg-gray-50 rounded px-3 py-2 whitespace-pre-wrap">{{ selectedGear.feeling }}</p>
          </div>

          <div v-if="selectedGear.photo">
            <span class="text-sm font-medium text-gray-500">图片</span>
            <img :src="selectedGear.photo" class="mt-1 w-40 h-40 object-cover rounded border border-gray-200" />
          </div>
        </div>

        <!-- 弹窗底部 -->
        <div class="flex justify-end px-6 py-4 border-t border-gray-200 bg-gray-50">
          <button
            @click="selectedGear = null"
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
import { getGears, deleteGear, type Gear } from '@/api/gears'
import Table from '@/components/common/Table.vue'
import Pagination from '@/components/common/Pagination.vue'

const columns = [
  { key: 'id', title: 'ID' },
  { key: 'user', title: '用户' },
  { key: 'name', title: '名称' },
  { key: 'category', title: '种类' },
  { key: 'price', title: '价格' },
  { key: 'created_at', title: '创建时间' }
]

const gears = ref<Gear[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const selectedGear = ref<Gear | null>(null)

const formatDate = (timestamp: number) => {
  if (!timestamp) return '--'
  return new Date(timestamp * 1000).toLocaleString('zh-CN')
}

const viewGear = (gear: Gear) => {
  selectedGear.value = gear
}

const fetchGears = async () => {
  try {
    const offset = (currentPage.value - 1) * pageSize.value
    const res = await getGears({ offset, limit: pageSize.value })
    gears.value = res.items
    total.value = res.total
  } catch (e) {
    console.error('Failed to fetch gears:', e)
  }
}

const confirmDelete = async (gear: Gear) => {
  if (confirm(`确定要删除装备 ${gear.name} 吗？`)) {
    try {
      await deleteGear(gear.id)
      await fetchGears()
    } catch (e) {
      console.error('Failed to delete gear:', e)
    }
  }
}

onMounted(fetchGears)
</script>
