<template>
  <view class="stepper">
    <view
      class="stepper-btn"
      :class="{ 'stepper-btn--disabled': !canMinus }"
      @tap="onMinus"
    >−</view>
    <text class="stepper-value">{{ modelValue }}</text>
    <view
      class="stepper-btn stepper-btn--plus"
      :class="{ 'stepper-btn--disabled': !canPlus }"
      @tap="onPlus"
    >+</view>
  </view>
</template>

<script setup lang="ts">
import { computed } from "vue";

const props = withDefaults(
  defineProps<{
    /** 当前值 */
    modelValue: number
    /** 最小值 */
    min?: number
    /** 最大值 */
    max?: number
    /** 步长 */
    step?: number
  }>(),
  {
    min: 0,
    max: 999,
    step: 1,
  },
);

const emit = defineEmits<{
  (e: "update:modelValue", value: number): void
}>();

const canMinus = computed(() => props.modelValue - props.step >= props.min);
const canPlus = computed(() => props.modelValue + props.step <= props.max);

function onMinus() {
  if (!canMinus.value) return;
  emit("update:modelValue", props.modelValue - props.step);
}

function onPlus() {
  if (!canPlus.value) return;
  emit("update:modelValue", props.modelValue + props.step);
}
</script>

<style scoped lang="scss">

.stepper {
  display: flex;
  align-items: center;
  gap: $space-md;
}

.stepper-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  font-size: 18px;
  background-color: $color-paper;
  color: $color-ink;
  transition: opacity 0.15s ease;
  
  &--plus {
    background-color: $color-olive;
    color: $color-white;
  }
  
  &--disabled {
    opacity: 0.3;
  }
  
  &:active:not(.stepper-btn--disabled) {
    opacity: 0.85;
  }
}

.stepper-value {
  min-width: 32px;
  text-align: center;
  font-size: 14px;
  font-weight: 600;
  color: $color-ink;
}
</style>
