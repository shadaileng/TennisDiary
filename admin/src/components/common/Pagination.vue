<template>
  <div class="flex items-center justify-between mt-4">
    <div class="text-sm text-gray-700">
      共 <span class="font-medium">{{ total }}</span> 条
    </div>
    <div class="flex items-center gap-2">
      <button
        @click="prev"
        :disabled="currentPage === 1"
        class="px-3 py-1 border rounded-md text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
      >
        上一页
      </button>
      <span class="text-sm text-gray-700">
        {{ currentPage }} / {{ totalPages }}
      </span>
      <button
        @click="next"
        :disabled="currentPage === totalPages"
        class="px-3 py-1 border rounded-md text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
      >
        下一页
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  total: number
  pageSize: number
  currentPage: number
}>()

const emit = defineEmits<{
  (e: 'update:currentPage', value: number): void
}>()

const totalPages = computed(() => Math.ceil(props.total / props.pageSize) || 1)

const prev = () => {
  if (props.currentPage > 1) {
    emit('update:currentPage', props.currentPage - 1)
  }
}

const next = () => {
  if (props.currentPage < totalPages.value) {
    emit('update:currentPage', props.currentPage + 1)
  }
}
</script>
