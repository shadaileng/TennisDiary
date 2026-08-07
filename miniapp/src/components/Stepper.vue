<template>
  <view class="flex items-center gap-3">
    <view
      class="stepper-btn w-8 h-8 flex items-center justify-center rounded-full bg-paper text-lg text-olive"
      :class="{ 'opacity-30': !canMinus }"
      @tap="onMinus"
    >−</view>
    <text class="min-w-8 text-center text-base font-semibold text-olive">{{ modelValue }}</text>
    <view
      class="stepper-btn w-8 h-8 flex items-center justify-center rounded-full bg-lime-dark text-lg text-white"
      :class="{ 'opacity-30': !canPlus }"
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

<style scoped>
.stepper-btn:active {
  opacity: 0.85;
}
</style>
