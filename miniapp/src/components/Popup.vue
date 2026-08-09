<template>
  <view v-if="show" class="popup-overlay">
    <!-- 遮罩 -->
    <view class="popup-mask" @tap="$emit('update:show', false)" />
    <!-- 内容区（底部弹出） -->
    <view
      class="popup-content"
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

<style scoped lang="scss">

.popup-overlay {
  position: fixed;
  inset: 0;
  z-index: 50;
}

.popup-mask {
  position: absolute;
  inset: 0;
  background-color: rgba(0, 0, 0, 0.4);
}

.popup-content {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: $color-white;
  border-top-left-radius: 20px;
  border-top-right-radius: 20px;
  padding: $space-lg;
  padding-bottom: env(safe-area-inset-bottom, 16px);
}
</style>
