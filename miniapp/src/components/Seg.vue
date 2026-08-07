<template>
  <view class="flex bg-paper rounded-card p-1">
    <view
      v-for="opt in options"
      :key="opt"
      class="flex-1 py-2 text-center text-sm rounded-card transition-colors"
      :class="opt === modelValue ? 'bg-lime-dark text-white font-medium' : 'text-olive-light'"
      @tap="$emit('update:modelValue', opt)"
    >
      {{ opt }}
    </view>
  </view>
</template>

<script setup lang="ts">
defineProps<{
  /** 当前选中值 */
  modelValue: string
  /** 选项列表 */
  options: readonly string[]
}>();

defineEmits<{
  (e: "update:modelValue", value: string): void
}>();
</script>
