<template>
  <view class="emoji-scale">
    <view
      v-for="opt in options"
      :key="opt.v"
      class="emoji-scale-item"
      :class="opt.v === modelValue ? 'emoji-scale-item--active' : ''"
      @tap="$emit('update:modelValue', opt.v)"
    >
      <text class="emoji-scale-emoji" :class="opt.v === modelValue ? '' : 'emoji-scale-emoji--dim'">
        {{ opt.emoji }}
      </text>
      <text class="emoji-scale-label" :class="opt.v === modelValue ? 'emoji-scale-label--active' : 'emoji-scale-label--inactive'">
        {{ opt.label }}
      </text>
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

<style scoped lang="scss">
@import "@/styles/tokens.scss";

.emoji-scale {
  display: flex;
  justify-content: space-between;
}

.emoji-scale-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 8px 4px;
  border-radius: 16px;
  transition: opacity 0.15s ease;
  
  &--active {
    background-color: $color-lime-soft;
  }
  
  &:active {
    opacity: 0.8;
  }
}

.emoji-scale-emoji {
  font-size: 24px;
  line-height: 1;
  
  &--dim {
    opacity: 0.4;
  }
}

.emoji-scale-label {
  font-size: 12px;
  
  &--active {
    color: $color-ink;
    font-weight: 500;
  }
  
  &--inactive {
    color: $color-olive-light;
  }
}
</style>
