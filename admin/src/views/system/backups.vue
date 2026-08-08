<template>
  <div class="p-6">
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-2xl font-bold text-gray-800">备份管理</h1>
      <button
        @click="createBackup"
        :disabled="creating"
        class="px-4 py-2 bg-olive-600 text-white rounded-lg hover:bg-olive-700 disabled:opacity-50"
      >
        {{ creating ? '备份中...' : '创建备份' }}
      </button>
    </div>

    <!-- 备份列表 -->
    <div class="bg-white rounded-lg shadow-md overflow-hidden">
      <table class="min-w-full divide-y divide-gray-200">
        <thead class="bg-gray-50">
          <tr>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">文件名</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">大小</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">创建时间</th>
            <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">操作</th>
          </tr>
        </thead>
        <tbody class="bg-white divide-y divide-gray-200">
          <tr v-for="backup in backups" :key="backup.name" class="hover:bg-gray-50">
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
              {{ backup.name }}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
              {{ backup.size }}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
              {{ formatDate(backup.created_at) }}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
              <button
                @click="restore(backup)"
                class="text-blue-600 hover:text-blue-800"
              >
                恢复
              </button>
            </td>
          </tr>
          <tr v-if="backups.length === 0">
            <td colspan="4" class="px-6 py-12 text-center text-gray-500">
              暂无备份
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { createBackup as createBackupApi, getBackups, restoreBackup, type Backup } from '@/api/system'

const backups = ref<Backup[]>([])
const creating = ref(false)

const formatDate = (date: string) => {
  return new Date(date).toLocaleString('zh-CN')
}

const fetchBackups = async () => {
  try {
    const data = await getBackups()
    backups.value = data.backups
  } catch (e) {
    console.error('Failed to fetch backups:', e)
  }
}

const createBackup = async () => {
  creating.value = true
  try {
    await createBackupApi()
    await fetchBackups()
  } catch (e) {
    console.error('Failed to create backup:', e)
  } finally {
    creating.value = false
  }
}

const restore = async (backup: Backup) => {
  if (confirm(`确定要恢复备份 ${backup.name} 吗？\n当前数据库将被覆盖！`)) {
    try {
      await restoreBackup(backup.name.replace('.db', ''))
      alert('恢复成功，请重启后端服务')
    } catch (e) {
      console.error('Failed to restore backup:', e)
    }
  }
}

onMounted(fetchBackups)
</script>
