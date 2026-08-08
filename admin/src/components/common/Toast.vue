<template>
  <Teleport to="body">
    <div class="fixed top-4 right-4 z-[100] flex flex-col gap-2">
      <TransitionGroup name="toast">
        <div
          v-for="toast in toasts"
          :key="toast.id"
          :class="toastClass(toast.type)"
          class="flex items-center gap-2 px-4 py-3 rounded-lg shadow-lg min-w-[280px] max-w-[420px]"
        >
          <component :is="iconComponent(toast.type)" class="w-5 h-5 flex-shrink-0" />
          <span class="flex-1 text-sm">{{ toast.message }}</span>
          <button @click="remove(toast.id)" class="ml-2 opacity-70 hover:opacity-100">
            <XMarkIcon class="w-4 h-4" />
          </button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { useToastStore, type Toast } from '@/stores/toast'
import { CheckCircleIcon, XCircleIcon, ExclamationTriangleIcon, InformationCircleIcon, XMarkIcon } from '@heroicons/vue/24/outline'
import { storeToRefs } from 'pinia'

const { toasts } = storeToRefs(useToastStore())
const { remove } = useToastStore()

const toastClass = (type: Toast['type']) => {
  const map: Record<Toast['type'], string> = {
    success: 'bg-green-50 text-green-800 border border-green-200',
    error: 'bg-red-50 text-red-800 border border-red-200',
    warning: 'bg-yellow-50 text-yellow-800 border border-yellow-200',
    info: 'bg-blue-50 text-blue-800 border border-blue-200'
  }
  return map[type]
}

const iconComponent = (type: Toast['type']) => {
  const map: Record<Toast['type'], typeof CheckCircleIcon> = {
    success: CheckCircleIcon,
    error: XCircleIcon,
    warning: ExclamationTriangleIcon,
    info: InformationCircleIcon
  }
  return map[type]
}
</script>

<style scoped>
.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}
.toast-enter-from {
  opacity: 0;
  transform: translateX(100%);
}
.toast-leave-to {
  opacity: 0;
  transform: translateX(100%);
}
</style>
