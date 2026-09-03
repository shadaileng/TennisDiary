<template>
  <Teleport to="body">
    <div v-if="visible" class="fixed inset-0 z-50 flex items-center justify-center">
      <div class="absolute inset-0 bg-black/70" @click="close" />
      <div class="relative bg-white rounded-lg shadow-xl max-w-4xl w-full mx-4 max-h-[90vh] flex flex-col">
        <!-- 头部 -->
        <div class="flex items-center justify-between px-6 py-3 border-b border-gray-200">
          <h2 class="text-lg font-semibold text-gray-800 truncate max-w-[500px]">{{ fileName }}</h2>
          <button class="text-gray-400 hover:text-gray-600 transition-colors" @click="close">
            <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <!-- 内容 -->
        <div class="flex-1 overflow-auto flex items-center justify-center p-4 bg-gray-50">
          <img
            v-if="isImage"
            :src="url"
            class="max-w-full max-h-[75vh] object-contain"
          />
          <video
            v-else-if="isVideo"
            :src="url"
            controls
            class="max-w-full max-h-[75vh]"
          />
          <audio
            v-else-if="isAudio"
            :src="url"
            controls
            class="w-full max-w-md"
          />
          <div v-else class="text-center py-12">
            <svg class="w-16 h-16 mx-auto text-gray-300 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <p class="text-gray-500">该文件类型不支持预览</p>
            <p class="text-sm text-gray-400 mt-1">{{ mimeType || '未知类型' }}</p>
          </div>
        </div>
        <!-- 底部 -->
        <div class="flex items-center justify-between px-6 py-3 border-t border-gray-200 bg-white">
          <span class="text-sm text-gray-500">{{ formatSize(sizeBytes) }}</span>
          <button
            type="button"
            @click="emit('download', props.fileId)"
            class="inline-flex items-center gap-1.5 px-3 py-1.5 bg-blue-500 text-white text-sm rounded hover:bg-blue-600 transition-colors"
          >
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            下载
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  visible: boolean
  fileId: number
  fileName: string
  url: string
  mimeType: string
  sizeBytes: number
}>()

const emit = defineEmits<{
  (e: 'update:visible', value: boolean): void
  (e: 'download', fileId: number): void
}>()

const close = () => emit('update:visible', false)

const isImage = computed(() => props.mimeType?.startsWith('image/'))
const isVideo = computed(() => props.mimeType?.startsWith('video/'))
const isAudio = computed(() => props.mimeType?.startsWith('audio/'))

function formatSize(bytes: number): string {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.min(Math.floor(Math.log(bytes) / Math.log(k)), sizes.length - 1)
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`
}
</script>
