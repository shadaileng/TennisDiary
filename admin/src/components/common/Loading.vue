<template>
  <Teleport to="body">
    <div
      v-if="loading"
      class="fixed inset-0 z-[90] flex items-center justify-center bg-white/60 backdrop-blur-[1px]"
    >
      <div class="flex flex-col items-center gap-3">
        <div class="w-10 h-10 border-4 border-olive-600 border-t-transparent rounded-full animate-spin" />
        <span class="text-sm text-gray-600">加载中...</span>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { storeToRefs } from 'pinia'
import { useAppStore } from '@/stores/app'

const { loading } = storeToRefs(useAppStore())
</script>
