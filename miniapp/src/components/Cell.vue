<template>
  <view
    class="flex items-center justify-between px-4 py-3.5"
    :class="{ 'press-cell': isLink }"
    @tap="$emit('click')"
  >
    <view class="flex flex-col flex-1 min-w-0">
      <text class="text-sm text-olive truncate">{{ title }}</text>
      <text v-if="label" class="text-xs text-olive-light mt-0.5 truncate">{{ label }}</text>
    </view>
    <view v-if="value || isLink" class="flex items-center gap-1 ml-2 shrink-0">
      <text v-if="value" class="text-sm text-olive-light">{{ value }}</text>
      <text v-if="isLink" class="text-olive-light text-sm leading-none">›</text>
    </view>
  </view>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    /** 主标题 */
    title: string
    /** 副标题 */
    label?: string
    /** 右侧值 */
    value?: string
    /** 是否可点击（显示箭头） */
    isLink?: boolean
  }>(),
  {
    label: "",
    value: "",
    isLink: false,
  },
);

defineEmits<{
  (e: "click"): void
}>();
</script>

<style scoped>
.press-cell:active {
  background-color: rgba(0, 0, 0, 0.03);
}
</style>
