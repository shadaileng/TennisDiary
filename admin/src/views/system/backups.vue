<template>
  <div class="p-6">
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-2xl font-bold text-gray-800">备份管理</h1>
      <div class="flex gap-3">
        <button
          @click="triggerUpload"
          :disabled="uploading"
          class="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 disabled:opacity-50"
        >
          {{ uploading ? '上传中...' : '上传备份' }}
        </button>
        <button
          @click="createBackup"
          :disabled="creating"
          class="px-4 py-2 bg-olive-600 text-white rounded-lg hover:bg-olive-700 disabled:opacity-50"
        >
          {{ creating ? '备份中...' : '创建备份' }}
        </button>
      </div>
      <input
        ref="fileInput"
        type="file"
        accept=".tar.gz,.db"
        class="hidden"
        @change="onFileSelected"
      />
    </div>

    <!-- 备份列表 -->
    <div class="bg-white rounded-lg shadow-md overflow-hidden">
      <table class="min-w-full divide-y divide-gray-200">
        <thead class="bg-gray-50">
          <tr>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">文件名</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">大小</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">创建时间</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">恢复状态</th>
            <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">操作</th>
          </tr>
        </thead>
        <tbody class="bg-white divide-y divide-gray-200">
          <tr v-for="backup in backups" :key="backup.name" class="hover:bg-gray-50">
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
              {{ backup.name }}
              <span
                v-if="backup.type === 'pre_restore'"
                class="ml-2 px-2 py-0.5 rounded text-xs bg-amber-100 text-amber-700"
              >
                恢复前兜底
              </span>
              <span
                v-else-if="backup.type === 'upload'"
                class="ml-2 px-2 py-0.5 rounded text-xs bg-green-100 text-green-700"
              >
                上传
              </span>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
              {{ backup.size }}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
              {{ formatIso(backup.created_at) }}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
              <span
                v-if="backup.status === 'restored'"
                class="inline-flex items-center px-2 py-0.5 rounded text-xs bg-blue-100 text-blue-700"
                :title="backup.restored_from_name ? `恢复时生成的兜底备份：${backup.restored_from_name}` : ''"
              >
                已恢复
              </span>
              <span
                v-else
                class="px-2 py-0.5 rounded text-xs bg-gray-100 text-gray-500"
              >
                未使用
              </span>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
              <button
                @click="download(backup)"
                class="text-olive-600 hover:text-olive-800 mr-3"
              >
                下载
              </button>
              <button
                @click="restore(backup)"
                class="text-blue-600 hover:text-blue-800 mr-3"
              >
                恢复
              </button>
              <button
                @click="remove(backup)"
                class="text-red-600 hover:text-red-800"
              >
                删除
              </button>
            </td>
          </tr>
          <tr v-if="backups.length === 0">
            <td colspan="5" class="px-6 py-12 text-center text-gray-500">
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
import axios from 'axios'
import { formatIso } from '@/utils/date'
import {
  createBackup as createBackupApi,
  getBackups,
  restoreBackup,
  deleteBackup,
  uploadBackup,
  type Backup
} from '@/api/system'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const backups = ref<Backup[]>([])
const creating = ref(false)
const uploading = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)

const triggerUpload = () => {
  fileInput.value?.click()
}

const onFileSelected = async (event: Event) => {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = '' // 允许重复选择同一文件
  if (!file) return

  uploading.value = true
  try {
    await uploadBackup(file)
    await fetchBackups()
  } catch (e) {
    console.error('Failed to upload backup:', e)
    alert('上传失败')
  } finally {
    uploading.value = false
  }
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

const download = async (backup: Backup) => {
  // 二进制下载需绕过 request 拦截器（其假设响应为 ApiResponse JSON）
  const base = import.meta.env.VITE_API_BASE_URL
  const url = `${base}/api/admin/system/backup/download/${encodeURIComponent(backup.name)}`
  try {
    const res = await axios.get(url, {
      responseType: 'blob',
      headers: { 'X-Auth-Token': authStore.token || '' }
    })
    const blobUrl = URL.createObjectURL(res.data)
    const a = document.createElement('a')
    a.href = blobUrl
    a.download = backup.name
    a.click()
    URL.revokeObjectURL(blobUrl)
  } catch (e) {
    console.error('Failed to download backup:', e)
    alert('下载失败')
  }
}

const restore = async (backup: Backup) => {
  if (confirm(`确定要恢复备份 ${backup.name} 吗？\n当前数据库将被覆盖！`)) {
    try {
      await restoreBackup(backup.name)
      alert('恢复成功，请重启后端服务')
      // 恢复完成后刷新列表，更新状态与兜底关联
      await fetchBackups()
    } catch (e) {
      console.error('Failed to restore backup:', e)
    }
  }
}

const remove = async (backup: Backup) => {
  if (!confirm(`确定要删除备份 ${backup.name} 吗？\n该操作不可恢复！`)) return
  try {
    await deleteBackup(backup.name)
    await fetchBackups()
  } catch (e) {
    console.error('Failed to delete backup:', e)
  }
}

onMounted(fetchBackups)
</script>
