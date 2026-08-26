<template>
  <Teleport to="body">
    <div
      v-if="visible"
      class="fixed bottom-4 right-4 z-[60] bg-white rounded-lg shadow-xl border border-gray-200 p-4 w-80"
    >
      <div class="flex items-center justify-between mb-2">
        <span class="text-sm font-medium text-gray-800 truncate max-w-[200px]">{{ fileName }}</span>
        <button
          v-if="!done"
          class="text-gray-400 hover:text-gray-600"
          @click="cancel"
        >
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
        <svg v-else class="w-5 h-5 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
        </svg>
      </div>
      <div class="w-full bg-gray-200 rounded-full h-2 mb-1">
        <div
          class="h-2 rounded-full transition-all duration-300"
          :class="done ? 'bg-green-500' : 'bg-blue-500'"
          :style="{ width: percent + '%' }"
        />
      </div>
      <div class="flex justify-between text-xs text-gray-400">
        <span>{{ formatSize(downloaded) }} / {{ formatSize(total) }}</span>
        <span>{{ percent }}%</span>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'

const props = defineProps<{
  visible: boolean
  fileName: string
  downloaded: number
  total: number
  done: boolean
}>()

const emit = defineEmits<{
  (e: 'cancel'): void
}>()

const percent = ref(0)

watch(
  () => [props.downloaded, props.total],
  ([dl, t]) => {
    percent.value = t > 0 ? Math.min(Math.round((dl / t) * 100), 100) : 0
  }
)

const cancel = () => emit('cancel')

function formatSize(bytes: number): string {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.min(Math.floor(Math.log(bytes) / Math.log(k)), sizes.length - 1)
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`
}
</script>
