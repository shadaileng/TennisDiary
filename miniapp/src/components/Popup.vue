<template>
  <view v-if="show" class="fixed inset-0 z-50">
    <!-- 遮罩 -->
    <view class="absolute inset-0 bg-black/40" @tap="$emit('update:show', false)" />
    <!-- 内容区（底部弹出） -->
    <view
      class="absolute left-0 right-0 bottom-0 bg-white rounded-t-[20px] p-4 pb-safe"
      @tap.stop
    >
      <slot />
    </view>
  </view>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    /** 是否显示 */
    show: boolean
  }>(),
  {
    show: false,
  },
);

defineEmits<{
  (e: "update:show", value: boolean): void
}>();
</script>
