<template>
  <div class="p-6">
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-2xl font-bold text-gray-800">文件管理</h1>
      <div class="flex gap-3">
        <select
          v-model="filterSource"
          class="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">全部来源</option>
          <option value="avatar">头像</option>
          <option value="gear_image">装备图片</option>
          <option value="video">视频</option>
          <option value="video_frame">视频帧</option>
          <option value="skeleton">骨架文件</option>
        </select>
        <input
          v-model="filterUserId"
          type="number"
          placeholder="用户 ID"
          class="px-3 py-2 border border-gray-300 rounded-lg text-sm w-28 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button
          @click="confirmCleanup"
          class="px-3 py-2 bg-orange-500 text-white rounded-lg text-sm hover:bg-orange-600 transition-colors whitespace-nowrap"
        >
          清理孤儿文件
        </button>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="grid grid-cols-4 gap-4 mb-6">
      <StatCard title="文件总数" :value="stats.total_count" icon="DocumentTextIcon" color="blue" />
      <StatCard
        title="总大小(MB)"
        :value="Number((stats.total_size_bytes / 1024 / 1024).toFixed(2))"
        icon="CheckCircleIcon"
        color="purple"
      />
      <StatCard title="头像" :value="stats.by_source?.avatar?.count || 0" icon="UsersIcon" color="green" />
      <StatCard title="视频" :value="stats.by_source?.video?.count || 0" icon="WrenchIcon" color="orange" />
    </div>

    <Table :columns="columns" :data="files" :row-clickable="true" @row-click="viewFile">
      <template #cell-size_bytes="{ value }">
        {{ formatSize(value) }}
      </template>

      <template #cell-ref_count="{ row }">
        <span :class="row.ref_count > 1 ? 'text-green-600 font-semibold' : 'text-gray-600'">
          {{ row.ref_count }}
        </span>
      </template>

      <template #cell-created_at="{ value }">
        {{ formatTs(value) }}
      </template>

      <template #actions="{ row }">
        <button @click="confirmDelete(row)" class="text-red-600 hover:text-red-800">删除</button>
      </template>
    </Table>

    <Pagination :total="total" :page-size="pageSize" v-model:current-page="currentPage" />

    <!-- 详情弹窗 -->
    <div v-if="selectedFile" class="fixed inset-0 z-50 flex items-center justify-center">
      <div class="absolute inset-0 bg-black/50" @click="selectedFile = null" />
      <div
        class="relative bg-white rounded-lg shadow-xl w-full max-w-2xl mx-4 max-h-[90vh] overflow-hidden flex flex-col"
      >
        <!-- 弹窗头部 -->
        <div class="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 class="text-lg font-semibold text-gray-800">文件详情</h2>
          <button
            @click="selectedFile = null"
            class="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        <!-- 弹窗内容 -->
        <div class="flex-1 overflow-y-auto px-6 py-4">
          <div class="grid grid-cols-2 gap-4 mb-6">
            <div>
              <span class="text-sm font-medium text-gray-500">ID</span>
              <p class="mt-1 text-sm text-gray-900">{{ selectedFile.id }}</p>
            </div>
            <div>
              <span class="text-sm font-medium text-gray-500">用户 ID</span>
              <p class="mt-1 text-sm text-gray-900">{{ selectedFile.user_id }}</p>
            </div>
            <div>
              <span class="text-sm font-medium text-gray-500">原始文件名</span>
              <p class="mt-1 text-sm text-gray-900">{{ selectedFile.original_name || '--' }}</p>
            </div>
            <div>
              <span class="text-sm font-medium text-gray-500">大小</span>
              <p class="mt-1 text-sm text-gray-900">{{ formatSize(selectedFile.size_bytes) }}</p>
            </div>
            <div>
              <span class="text-sm font-medium text-gray-500">上传来源</span>
              <p class="mt-1 text-sm text-gray-900">{{ selectedFile.upload_source }}</p>
            </div>
            <div>
              <span class="text-sm font-medium text-gray-500">MIME 类型</span>
              <p class="mt-1 text-sm text-gray-900">{{ selectedFile.mime_type || '--' }}</p>
            </div>
            <div>
              <span class="text-sm font-medium text-gray-500">引用计数</span>
              <p
                class="mt-1 text-sm"
                :class="
                  selectedFile.ref_count > 1 ? 'text-green-600 font-semibold' : 'text-gray-900'
                "
              >
                {{ selectedFile.ref_count }}
              </p>
            </div>
            <div>
              <span class="text-sm font-medium text-gray-500">上传时间</span>
              <p class="mt-1 text-sm text-gray-900">{{ formatTs(selectedFile.created_at) }}</p>
            </div>
            <div>
              <span class="text-sm font-medium text-gray-500">MD5</span>
              <p class="mt-1 text-xs text-gray-900 font-mono break-all">{{ selectedFile.md5 }}</p>
            </div>
            <div>
              <span class="text-sm font-medium text-gray-500">相对路径</span>
              <p class="mt-1 text-xs text-gray-900 font-mono break-all">
                {{ selectedFile.rel_path }}
              </p>
            </div>
          </div>

          <!-- 派生文件列表 -->
          <div v-if="selectedFile.derived_files?.length" class="border-t pt-4">
            <h3 class="text-sm font-medium text-gray-500 mb-2">
              关联文件（{{ selectedFile.derived_files.length }}）
            </h3>
            <div class="space-y-2">
              <div
                v-for="derived in selectedFile.derived_files"
                :key="derived.id"
                class="bg-gray-50 rounded p-3 text-sm flex justify-between items-start gap-3"
              >
                <div class="min-w-0">
                  <p class="font-mono text-xs break-all">{{ derived.rel_path }}</p>
                  <p class="text-xs text-gray-500 mt-1">
                    {{ derived.upload_source }} · {{ derived.mime_type || '--' }}
                  </p>
                </div>
                <span class="text-xs text-gray-500 whitespace-nowrap">
                  {{ formatSize(derived.size_bytes) }}
                </span>
              </div>
            </div>
          </div>
        </div>

        <!-- 弹窗底部 -->
        <div class="flex justify-end px-6 py-4 border-t border-gray-200 bg-gray-50">
          <button
            @click="selectedFile = null"
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
import { ref, watch, onMounted } from 'vue'
import { getFiles, getFileStats, deleteFile, cleanupFiles, type AdminFile, type FileStats } from '@/api/files'
import Table from '@/components/common/Table.vue'
import Pagination from '@/components/common/Pagination.vue'
import StatCard from '@/components/common/StatCard.vue'
import { formatTs } from '@/utils/date'

const columns = [
  { key: 'id', title: 'ID' },
  { key: 'user_id', title: '用户' },
  { key: 'original_name', title: '文件名' },
  { key: 'size_bytes', title: '大小' },
  { key: 'upload_source', title: '来源' },
  { key: 'ref_count', title: '引用' },
  { key: 'created_at', title: '上传时间' }
]

const files = ref<AdminFile[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const filterSource = ref('')
const filterUserId = ref('')
const selectedFile = ref<AdminFile | null>(null)
const stats = ref<FileStats>({ total_count: 0, total_size_bytes: 0, by_source: {} })

function formatSize(bytes: number): string {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.min(Math.floor(Math.log(bytes) / Math.log(k)), sizes.length - 1)
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`
}

const fetchFiles = async () => {
  try {
    const offset = (currentPage.value - 1) * pageSize.value
    const params: Record<string, unknown> = { offset, limit: pageSize.value }
    if (filterSource.value) params.upload_source = filterSource.value
    if (filterUserId.value) params.user_id = Number(filterUserId.value)
    const res = await getFiles(params)
    files.value = res.items
    total.value = res.total
  } catch (e) {
    console.error('Failed to fetch files:', e)
  }
}

const fetchStats = async () => {
  try {
    stats.value = await getFileStats()
  } catch (e) {
    console.error('Failed to fetch file stats:', e)
  }
}

const viewFile = (file: AdminFile) => {
  selectedFile.value = file
}

const confirmDelete = async (file: AdminFile) => {
  if (confirm(`确定要删除文件 ${file.original_name || file.rel_path} 吗？`)) {
    try {
      await deleteFile(file.id)
      await fetchFiles()
      await fetchStats()
    } catch (e) {
      console.error('Failed to delete file:', e)
    }
  }
}

const confirmCleanup = async () => {
  if (confirm('确定要清理已删除超过 30 天的孤儿文件吗？')) {
    try {
      const res = await cleanupFiles(30)
      alert(`清理完成，共清理 ${res.cleaned} 个文件`)
      await fetchStats()
    } catch (e) {
      console.error('Failed to cleanup files:', e)
    }
  }
}

watch([filterSource, filterUserId], () => {
  currentPage.value = 1
  fetchFiles()
})

watch(currentPage, fetchFiles)

onMounted(() => {
  fetchFiles()
  fetchStats()
})
</script>
