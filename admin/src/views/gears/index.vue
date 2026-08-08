<template>
  <div class="p-6">
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-2xl font-bold text-gray-800">装备管理</h1>
    </div>

    <Table :columns="columns" :data="gears">
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

const formatDate = (date: string) => {
  return new Date(date).toLocaleDateString('zh-CN')
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
