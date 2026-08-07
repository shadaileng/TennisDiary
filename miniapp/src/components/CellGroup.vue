<template>
  <view class="mx-4 mb-4">
    <text v-if="title" class="block px-1 mb-1.5 text-xs text-olive-light">{{ title }}</text>
    <view class="bg-white rounded-card overflow-hidden">
      <slot />
    </view>
  </view>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    /** 分组标题 */
    title?: string
  }>(),
  {
    title: "",
  },
);
</script>
