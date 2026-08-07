<template>
  <view class="flex justify-between">
    <view
      v-for="opt in options"
      :key="opt.v"
      class="flex flex-col items-center gap-1 py-2 px-1 rounded-card transition-colors"
      :class="opt.v === modelValue ? 'bg-lime-soft' : ''"
      @tap="$emit('update:modelValue', opt.v)"
    >
      <text
        class="text-2xl leading-none"
        :class="opt.v === modelValue ? '' : 'opacity-40'"
      >{{ opt.emoji }}</text>
      <text
        class="text-xs"
        :class="opt.v === modelValue ? 'text-olive font-medium' : 'text-olive-light'"
      >{{ opt.label }}</text>
    </view>
  </view>
</template>

<script setup lang="ts">
export interface EmojiScaleOption {
  v: number
  label: string
  emoji: string
}

defineProps<{
  /** 当前选中值 */
  modelValue: number
  /** 选项列表 */
  options: readonly EmojiScaleOption[]
}>();

defineEmits<{
  (e: "update:modelValue", value: number): void
}>();
</script>
