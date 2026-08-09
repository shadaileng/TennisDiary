<template>
  <view class="cell-group">
    <text v-if="title" class="cell-group-title">{{ title }}</text>
    <view class="cell-group-content">
      <slot />
    </view>
  </view>
</template>

<script setup lang="ts">
defineProps<{
  /** 标题 */
  title?: string
}>();
</script>

<style scoped lang="scss">

.cell-group {
  margin-bottom: $space-md;
}

.cell-group-title {
  display: block;
  padding: 0 $space-xs;
  margin-bottom: $space-sm;
  font-size: 12px;
  color: $color-olive-light;
}

.cell-group-content {
  background-color: $color-white;
  border-radius: $radius-card;
  overflow: hidden;
  box-shadow: $shadow-card;
}
</style>
