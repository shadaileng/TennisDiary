<template>
  <view class="flex flex-col items-center justify-center py-12 px-6">
    <text v-if="icon" class="text-5xl leading-none mb-3">{{ icon }}</text>
    <text class="text-sm text-olive-light text-center">{{ text || "暂无数据" }}</text>
    <view
      v-if="buttonText"
      class="mt-4 press-btn bg-lime-dark text-white text-sm font-medium px-6 py-2 rounded-full"
      @tap="$emit('action')"
    >
      {{ buttonText }}
    </view>
  </view>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    /** 空态图标（emoji） */
    icon?: string
    /** 空态文案 */
    text?: string
    /** 操作按钮文案（不传则不显示按钮） */
    buttonText?: string
  }>(),
  {
    icon: "📭",
    text: "暂无数据",
    buttonText: "",
  },
);

defineEmits<{
  (e: "action"): void
}>();
</script>

<style scoped>
.press-btn:active {
  opacity: 0.9;
}
</style>
