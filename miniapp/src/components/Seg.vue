<template>
  <view class="seg">
    <view
      v-for="opt in options"
      :key="opt"
      class="seg-item"
      :class="opt === modelValue ? 'seg-item--active' : 'seg-item--inactive'"
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

<style scoped lang="scss">

.seg {
  display: flex;
  background-color: $color-paper;
  border-radius: $radius-card;
  padding: 4px;
}

.seg-item {
  flex: 1;
  padding: 8px 0;
  text-align: center;
  font-size: 14px;
  border-radius: $radius-card;
  transition: opacity 0.15s ease;
  
  &--active {
    background-color: $color-olive;
    color: $color-white;
    font-weight: 500;
  }
  
  &--inactive {
    color: $color-olive-light;
  }
  
  &:active {
    opacity: 0.8;
  }
}
</style>
