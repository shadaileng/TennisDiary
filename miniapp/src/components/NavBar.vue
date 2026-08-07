<template>
  <view class="nav-bar sticky top-0 z-10 bg-paper/95 backdrop-blur">
    <view class="flex items-center h-12 px-4">
      <!-- 左侧：返回或占位 -->
      <view class="w-10">
        <text
          v-if="showBack"
          class="text-xl text-olive leading-none"
          @tap="$emit('back')"
        >‹</text>
      </view>

      <!-- 标题 -->
      <text class="flex-1 text-center text-base font-semibold text-olive truncate">
        {{ title }}
      </text>

      <!-- 右侧操作 -->
      <view class="w-10 flex justify-end">
        <text
          v-if="rightText"
          class="text-sm text-lime-dark font-medium"
          @tap="$emit('right')"
        >{{ rightText }}</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    /** 标题 */
    title: string
    /** 是否显示返回箭头 */
    showBack?: boolean
    /** 右侧操作文案（不传则不显示） */
    rightText?: string
  }>(),
  {
    showBack: false,
    rightText: "",
  },
);

defineEmits<{
  (e: "back"): void
  (e: "right"): void
}>();
</script>
