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
        <select
          v-model="filterUsageStatus"
          class="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">全部状态</option>
          <option value="in_use">使用中</option>
          <option value="unreferenced">可清除·引用失效</option>
          <option value="marked_deleted">可清除·已软删</option>
          <option value="orphan">可清除·孤儿</option>
        </select>
        <input
          v-model="filterUserId"
          type="number"
          placeholder="用户 ID"
          class="px-3 py-2 border border-gray-300 rounded-lg text-sm w-28 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button
          @click="confirmScan"
          :disabled="scanning"
          class="px-3 py-2 bg-blue-500 text-white rounded-lg text-sm hover:bg-blue-600 transition-colors whitespace-nowrap disabled:opacity-50"
        >
          {{ scanning ? '扫描中...' : '扫描孤立文件' }}
        </button>
        <button
          @click="confirmCleanup"
          class="px-3 py-2 bg-orange-500 text-white rounded-lg text-sm hover:bg-orange-600 transition-colors whitespace-nowrap"
        >
          清理孤儿文件
        </button>
        <button
          v-if="selectedFiles.length > 0"
          @click="confirmBatchDelete"
          class="px-3 py-2 bg-red-600 text-white rounded-lg text-sm hover:bg-red-700 transition-colors whitespace-nowrap"
        >
          批量删除 ({{ selectedFiles.length }})
        </button>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="grid grid-cols-5 gap-4 mb-6">
      <StatCard title="文件总数" :value="stats.total_count" icon="DocumentTextIcon" color="blue" />
      <StatCard
        title="总大小(MB)"
        :value="Number((stats.total_size_bytes / 1024 / 1024).toFixed(2))"
        icon="CheckCircleIcon"
        color="purple"
      />
      <StatCard title="头像" :value="stats.by_source?.avatar?.count || 0" icon="UsersIcon" color="green" />
      <StatCard title="视频" :value="stats.by_source?.video?.count || 0" icon="WrenchIcon" color="orange" />
      <StatCard title="可清除" :value="stats.unreferenced_count || 0" icon="DocumentTextIcon" color="orange" />
    </div>

    <Table
      ref="tableRef"
      :columns="columns"
      :data="files"
      :row-clickable="true"
      :selectable="true"
      row-key="id"
      :row-selectable="isClearable"
      @row-click="viewFile"
      @selection-change="onSelectionChange"
    >
      <template #cell-size_bytes="{ value }">
        {{ formatSize(value) }}
      </template>

      <template #cell-usage_status="{ row }">
        <span
          :class="usageBadgeClass(row.usage_status)"
          :title="row.usage_reason"
          class="inline-block px-2 py-0.5 rounded text-xs font-medium"
        >
          {{ usageBadgeLabel(row.usage_status) }}
        </span>
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
        <div class="flex items-center gap-2">
          <button @click="openPreview(row)" class="text-blue-600 hover:text-blue-800">预览</button>
          <button @click="startDownload(row)" class="text-green-600 hover:text-green-800">下载</button>
          <button @click="confirmDelete(row)" class="text-red-600 hover:text-red-800">删除</button>
        </div>
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
              <p class="mt-1 text-sm text-gray-900 break-all">{{ selectedFile.original_name || '--' }}</p>
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
              <span class="text-sm font-medium text-gray-500">使用状态</span>
              <p class="mt-1 text-sm">
                <span
                  :class="usageBadgeClass(selectedFile.usage_status)"
                  :title="selectedFile.usage_reason"
                  class="inline-block px-2 py-0.5 rounded text-xs font-medium"
                >
                  {{ usageBadgeLabel(selectedFile.usage_status) }}
                </span>
                <span v-if="selectedFile.usage_reason" class="ml-2 text-gray-500 text-xs">
                  — {{ selectedFile.usage_reason }}
                </span>
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
        <div class="flex justify-between px-6 py-4 border-t border-gray-200 bg-gray-50">
          <div class="flex gap-2">
            <button
              v-if="selectedFile"
              @click="openPreview(selectedFile)"
              class="px-3 py-2 bg-blue-500 text-white text-sm rounded-md hover:bg-blue-600 transition-colors"
            >
              预览
            </button>
            <button
              v-if="selectedFile"
              @click="startDownload(selectedFile)"
              class="px-3 py-2 bg-green-500 text-white text-sm rounded-md hover:bg-green-600 transition-colors"
            >
              下载
            </button>
          </div>
          <button
            @click="selectedFile = null"
            class="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 transition-colors"
          >
            关闭
          </button>
        </div>
      </div>
    </div>

    <!-- 扫描结果弹窗 -->
    <div v-if="scanResult" class="fixed inset-0 z-50 flex items-center justify-center">
      <div class="absolute inset-0 bg-black/50" @click="scanResult = null" />
      <div
        class="relative bg-white rounded-lg shadow-xl w-full max-w-4xl mx-4 max-h-[90vh] overflow-hidden flex flex-col"
      >
        <!-- 弹窗头部 -->
        <div class="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 class="text-lg font-semibold text-gray-800">扫描结果</h2>
          <button
            @click="scanResult = null"
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
          <!-- 统计信息 -->
          <div class="grid grid-cols-4 gap-4 mb-6">
            <div class="bg-blue-50 rounded-lg p-4 text-center">
              <p class="text-2xl font-bold text-blue-600">{{ scanResult.total_files }}</p>
              <p class="text-sm text-gray-600">总文件</p>
            </div>
            <div class="bg-green-50 rounded-lg p-4 text-center">
              <p class="text-2xl font-bold text-green-600">{{ scanResult.registered_files }}</p>
              <p class="text-sm text-gray-600">已注册</p>
            </div>
            <div class="bg-orange-50 rounded-lg p-4 text-center">
              <p class="text-2xl font-bold text-orange-600">{{ scanResult.orphan_files }}</p>
              <p class="text-sm text-gray-600">未注册</p>
            </div>
            <div class="bg-purple-50 rounded-lg p-4 text-center">
              <p class="text-2xl font-bold text-purple-600">{{ formatSize(scanResult.total_orphan_size) }}</p>
              <p class="text-sm text-gray-600">未注册大小</p>
            </div>
          </div>

          <!-- 未注册文件列表 -->
          <div v-if="scanResult.orphans.length > 0">
            <div class="flex justify-between items-center mb-3">
              <h3 class="text-sm font-medium text-gray-700">
                未注册文件列表
              </h3>
              <div class="flex gap-2">
                <button
                  @click="toggleSelectAll"
                  class="px-3 py-1 text-sm bg-gray-200 rounded hover:bg-gray-300"
                >
                  {{ selectedOrphans.length === scanResult.orphans.length ? '取消全选' : '全选' }}
                </button>
                <button
                  @click="confirmRegisterSelected"
                  :disabled="selectedOrphans.length === 0"
                  class="px-3 py-1 text-sm bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50"
                >
                  纳入管理 ({{ selectedOrphans.length }})
                </button>
                <button
                  @click="confirmCleanupSelected"
                  :disabled="selectedOrphans.length === 0"
                  class="px-3 py-1 text-sm bg-red-500 text-white rounded hover:bg-red-600 disabled:opacity-50"
                >
                  立即清理 ({{ selectedOrphans.length }})
                </button>
              </div>
            </div>

            <div class="border rounded-lg overflow-hidden">
              <table class="w-full text-sm">
                <thead class="bg-gray-50">
                  <tr>
                    <th class="px-4 py-2 text-left w-10">
                      <input
                        type="checkbox"
                        :checked="selectedOrphans.length === scanResult.orphans.length"
                        @change="toggleSelectAll"
                        class="rounded"
                      />
                    </th>
                    <th class="px-4 py-2 text-left">文件路径</th>
                    <th class="px-4 py-2 text-right">大小</th>
                    <th class="px-4 py-2 text-left">修改时间</th>
                    <th class="px-4 py-2 text-center">用户</th>
                    <th class="px-4 py-2 text-center">来源</th>
                    <th class="px-4 py-2 text-center">状态</th>
                    <th class="px-4 py-2 text-center">操作</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-gray-200">
                  <tr
                    v-for="orphan in scanResult.orphans"
                    :key="orphan.rel_path"
                    class="hover:bg-gray-50"
                  >
                    <td class="px-4 py-2">
                      <input
                        type="checkbox"
                        :value="orphan.rel_path"
                        v-model="selectedOrphans"
                        class="rounded"
                      />
                    </td>
                    <td class="px-4 py-2 font-mono text-xs break-all">{{ orphan.rel_path }}</td>
                    <td class="px-4 py-2 text-right text-gray-600">{{ formatSize(orphan.size_bytes) }}</td>
                    <td class="px-4 py-2 text-gray-600">{{ formatTs(orphan.modified_at) }}</td>
                    <td class="px-4 py-2 text-center">{{ orphan.inferred_user_id || '--' }}</td>
                    <td class="px-4 py-2 text-center text-gray-600">{{ orphan.inferred_source }}</td>
                    <td class="px-4 py-2 text-center">
                      <span
                        :class="usageBadgeClass(orphan.usage_status)"
                        :title="orphan.usage_reason"
                        class="inline-block px-2 py-0.5 rounded text-xs font-medium"
                      >
                        {{ usageBadgeLabel(orphan.usage_status) }}
                      </span>
                    </td>
                    <td class="px-4 py-2 text-center">
                      <button
                        @click="confirmRegisterSingle(orphan.rel_path)"
                        class="text-blue-600 hover:text-blue-800"
                      >
                        纳入
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <div v-else class="text-center py-8 text-gray-500">
            没有发现未注册的文件
          </div>
        </div>

        <!-- 弹窗底部 -->
        <div class="flex justify-end px-6 py-4 border-t border-gray-200 bg-gray-50">
          <button
            @click="confirmRegisterAll"
            class="px-4 py-2 bg-green-500 text-white rounded-md hover:bg-green-600 transition-colors mr-3"
          >
            一键纳入所有
          </button>
          <button
            @click="scanResult = null"
            class="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 transition-colors"
          >
            关闭
          </button>
        </div>
      </div>
    </div>
  </div>

  <!-- 文件预览 -->
  <FilePreview
    v-if="previewInfo"
    v-model:visible="previewVisible"
    :file-id="previewInfo.id"
    :file-name="previewInfo.original_name"
    :url="previewInfo.preview_url"
    :mime-type="previewInfo.mime_type"
    :size-bytes="previewInfo.size_bytes"
  />

  <!-- 流式下载进度条 -->
  <DownloadProgress
    :visible="dl.visible"
    :file-name="dl.fileName"
    :downloaded="dl.downloaded"
    :total="dl.total"
    :done="dl.done"
    @cancel="cancelDownload"
  />
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import {
  getFiles,
  getFileStats,
  deleteFile,
  batchDeleteFiles,
  cleanupFiles,
  scanOrphanFiles,
  registerFiles,
  registerAllFiles,
  cleanupOrphanFiles,
  getPreviewInfo,
  getDownloadUrl,
  type AdminFile,
  type FileStats,
  type ScanResultResponse,
  type PreviewInfo
} from '@/api/files'
import Table from '@/components/common/Table.vue'
import Pagination from '@/components/common/Pagination.vue'
import StatCard from '@/components/common/StatCard.vue'
import FilePreview from '@/components/common/FilePreview.vue'
import DownloadProgress from '@/components/common/DownloadProgress.vue'
import { formatTs } from '@/utils/date'

const columns = [
  { key: 'id', title: 'ID', width: 48 },
  { key: 'user_id', title: '用户', width: 40 },
  { key: 'original_name', title: '文件名', wrap: true },
  { key: 'size_bytes', title: '大小', width: 64 },
  { key: 'upload_source', title: '来源', width: 64 },
  { key: 'usage_status', title: '状态', width: 64 },
  { key: 'ref_count', title: '引用', width: 40 },
  { key: 'created_at', title: '上传时间', width: 170 }
]

const files = ref<AdminFile[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const filterSource = ref('')
const filterUsageStatus = ref('')
const filterUserId = ref('')
const selectedFile = ref<AdminFile | null>(null)
const stats = ref<FileStats>({ total_count: 0, total_size_bytes: 0, by_source: {} })
const selectedFiles = ref<AdminFile[]>([])
const tableRef = ref<InstanceType<typeof Table> | null>(null)

const isClearable = (file: AdminFile): boolean => file.usage_status !== 'in_use'

const onSelectionChange = (rows: AdminFile[]) => {
  selectedFiles.value = rows
}

// 扫描相关状态
const scanning = ref(false)
const scanResult = ref<ScanResultResponse | null>(null)
const selectedOrphans = ref<string[]>([])

// 预览相关状态
const previewVisible = ref(false)
const previewInfo = ref<PreviewInfo | null>(null)

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
    if (filterUsageStatus.value) params.usage_status = filterUsageStatus.value
    const res = await getFiles(params)
    files.value = res.items
    total.value = res.total
  } catch (e) {
    console.error('Failed to fetch files:', e)
  }
}

const usageBadgeLabel = (status: string): string => {
  const map: Record<string, string> = {
    in_use: '使用中',
    unreferenced: '可清除',
    marked_deleted: '可清除',
    orphan: '可清除·孤儿',
  }
  return map[status] || status
}

const usageBadgeClass = (status: string): string => {
  const map: Record<string, string> = {
    in_use: 'bg-green-100 text-green-700',
    unreferenced: 'bg-orange-100 text-orange-700',
    marked_deleted: 'bg-gray-200 text-gray-600',
    orphan: 'bg-red-100 text-red-700',
  }
  return map[status] || 'bg-gray-100 text-gray-600'
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

// 流式下载状态
const dl = ref({ visible: false, fileName: '', downloaded: 0, total: 0, done: false })
let dlAbort: AbortController | null = null

const startDownload = async (file: AdminFile) => {
  const fileName = file.original_name || file.rel_path
  const token = localStorage.getItem('admin_token')
  const url = getDownloadUrl(file.id)

  // Chromium: showSaveFilePicker 流式写入磁盘（零内存）
  if (typeof window.showSaveFilePicker === 'function') {
    let fileHandle: FileSystemFileHandle
    try {
      fileHandle = await window.showSaveFilePicker({
        suggestedName: fileName,
        types: [{ description: '文件', accept: { 'application/octet-stream': [] } }],
      })
    } catch {
      return // 用户取消选择
    }

    dl.value = { visible: true, fileName, downloaded: 0, total: file.size_bytes, done: false }
    dlAbort = new AbortController()

    try {
      const resp = await fetch(url, {
        headers: { 'X-Auth-Token': token || '' },
        signal: dlAbort.signal,
      })
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`)

      const writable = await fileHandle.createWritable()
      const reader = resp.body!.getReader()
      const contentLength = Number(resp.headers.get('Content-Length') || file.size_bytes)
      dl.value = { ...dl.value, total: contentLength }

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        await writable.write(value)
        dl.value = { ...dl.value, downloaded: dl.value.downloaded + value.length }
      }

      await writable.close()
      dl.value = { ...dl.value, done: true }
      setTimeout(() => { dl.value.visible = false }, 2000)
    } catch (e) {
      if (e instanceof DOMException && e.name === 'AbortError') return
      console.error('Download failed:', e)
      dl.value.visible = false
    } finally {
      dlAbort = null
    }
  } else {
    // 非 Chromium fallback：<a> 标签原生下载
    const a = document.createElement('a')
    a.href = url + (token ? `?token=${encodeURIComponent(token)}` : '')
    a.download = fileName
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
  }
}

const cancelDownload = () => {
  dlAbort?.abort()
  dl.value.visible = false
}

const openPreview = async (file: AdminFile) => {
  try {
    const info = await getPreviewInfo(file.id)
    previewInfo.value = info
    previewVisible.value = true
  } catch (e) {
    console.error('Failed to load preview:', e)
  }
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

const confirmBatchDelete = async () => {
  if (selectedFiles.value.length === 0) return
  const count = selectedFiles.value.length
  if (confirm(`确定要删除选中的 ${count} 个可清除文件吗？此操作会软删文件记录并释放物理存储，不可恢复。`)) {
    try {
      const res = await batchDeleteFiles(selectedFiles.value.map((f) => f.id))
      alert(`删除完成：成功 ${res.deleted} 个，跳过 ${res.skipped} 个，物理清理 ${res.disk_removed} 个`)
      tableRef.value?.clearSelection()
      await fetchFiles()
      await fetchStats()
    } catch (e) {
      console.error('Failed to batch delete files:', e)
      alert('批量删除失败，请稍后重试')
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

// 扫描相关函数
const confirmScan = async () => {
  scanning.value = true
  try {
    const result = await scanOrphanFiles()
    scanResult.value = result
    selectedOrphans.value = []
  } catch (e) {
    console.error('Failed to scan files:', e)
    alert('扫描失败，请稍后重试')
  } finally {
    scanning.value = false
  }
}

const toggleSelectAll = () => {
  if (!scanResult.value) return
  if (selectedOrphans.value.length === scanResult.value.orphans.length) {
    selectedOrphans.value = []
  } else {
    selectedOrphans.value = scanResult.value.orphans.map((o) => o.rel_path)
  }
}

const confirmRegisterSelected = async () => {
  if (selectedOrphans.value.length === 0) return
  if (confirm(`确定要将 ${selectedOrphans.value.length} 个文件纳入管理吗？`)) {
    try {
      const res = await registerFiles(selectedOrphans.value)
      alert(`成功注册 ${res.registered} 个文件`)
      scanResult.value = null
      await fetchFiles()
      await fetchStats()
    } catch (e) {
      console.error('Failed to register files:', e)
      alert('注册失败，请稍后重试')
    }
  }
}

const confirmCleanupSelected = async () => {
  if (selectedOrphans.value.length === 0) return
  if (confirm(`确定要立即删除选中的 ${selectedOrphans.value.length} 个孤儿文件吗？此操作不可恢复。`)) {
    try {
      const res = await cleanupOrphanFiles(selectedOrphans.value)
      alert(`清理完成，共删除 ${res.cleaned} 个文件`)
      scanResult.value = null
      await fetchFiles()
      await fetchStats()
    } catch (e) {
      console.error('Failed to cleanup orphans:', e)
      alert('清理失败，请稍后重试')
    }
  }
}

const confirmRegisterSingle = async (relPath: string) => {
  if (confirm(`确定要将文件 ${relPath} 纳入管理吗？`)) {
    try {
      const res = await registerFiles([relPath])
      alert(`成功注册 ${res.registered} 个文件`)
      // 更新扫描结果
      if (scanResult.value) {
        scanResult.value.orphans = scanResult.value.orphans.filter(
          (o) => o.rel_path !== relPath
        )
        scanResult.value.orphan_files = scanResult.value.orphans.length
        scanResult.value.registered_files += 1
        selectedOrphans.value = selectedOrphans.value.filter((p) => p !== relPath)
      }
      await fetchFiles()
      await fetchStats()
    } catch (e) {
      console.error('Failed to register file:', e)
      alert('注册失败，请稍后重试')
    }
  }
}

const confirmRegisterAll = async () => {
  if (confirm('确定要将所有未注册文件纳入管理吗？')) {
    try {
      const res = await registerAllFiles()
      alert(`成功注册 ${res.registered} 个文件`)
      scanResult.value = null
      await fetchFiles()
      await fetchStats()
    } catch (e) {
      console.error('Failed to register all files:', e)
      alert('注册失败，请稍后重试')
    }
  }
}

watch([filterSource, filterUserId], () => {
  currentPage.value = 1
  fetchFiles()
})

watch(filterUsageStatus, () => {
  currentPage.value = 1
  fetchFiles()
})

watch(currentPage, fetchFiles)

onMounted(() => {
  fetchFiles()
  fetchStats()
})
</script>
