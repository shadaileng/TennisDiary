<template>
  <div class="flex items-center justify-between mt-4">
    <div class="text-sm text-gray-700">
      共 <span class="font-medium">{{ total }}</span> 条
    </div>
    <div class="flex items-center gap-1">
      <button
        @click="prev"
        :disabled="currentPage === 1"
        class="px-3 py-1 border rounded-md text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
      >
        上一页
      </button>
      <template v-for="(p, idx) in pages" :key="idx">
        <span
          v-if="p === '...'"
          class="px-2 py-1 text-sm text-gray-400 select-none"
        >
          …
        </span>
        <button
          v-else
          @click="go(p)"
          :disabled="p === currentPage"
          :class="[
            'px-3 py-1 border rounded-md text-sm',
            p === currentPage
              ? 'bg-blue-600 border-blue-600 text-white cursor-default'
              : 'hover:bg-gray-50',
          ]"
        >
          {{ p }}
        </button>
      </template>
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

const pages = computed<(number | '...')[]>(() => {
  const total = totalPages.value
  if (total <= 1) return [1]
  let start = props.currentPage - 1
  let end = props.currentPage + 1
  if (start < 2) {
    const shift = 2 - start
    start += shift
    end += shift
  }
  if (end > total - 1) {
    const shift = end - (total - 1)
    end -= shift
    start -= shift
  }
  start = Math.max(start, 2)
  end = Math.min(end, total - 1)

  const result: (number | '...')[] = [1]
  if (start > 2) result.push('...')
  for (let i = start; i <= end; i++) result.push(i)
  if (end < total - 1) result.push('...')
  if (total > 1) result.push(total)
  return result
})

const go = (p: number) => {
  if (p !== props.currentPage) {
    emit('update:currentPage', p)
  }
}

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
