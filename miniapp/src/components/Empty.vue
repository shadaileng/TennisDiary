<template>
  <view class="empty">
    <view class="empty-icon-wrap">
      <text class="empty-icon">{{ icon }}</text>
    </view>
    <text class="empty-text">{{ text || "暂无数据" }}</text>
    <view
      v-if="buttonText"
      class="empty-btn press-btn"
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

<style scoped lang="scss">

.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 64px $space-lg;
}

.empty-icon-wrap {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background-color: var(--color-accent-soft, $color-lime-soft);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: $space-lg;
}

.empty-icon {
  font-size: 36px;
  line-height: 1;
}

.empty-text {
  font-size: 14px;
  color: $color-olive-light;
  text-align: center;
  line-height: 1.6;
  margin-bottom: $space-lg;
}

.empty-btn {
  background-color: var(--color-accent-dark, $color-lime-dark);
  color: $color-white;
  font-size: 14px;
  font-weight: 500;
  padding: $space-md $space-2xl;
  border-radius: 9999px;
  transition: opacity 0.15s ease;
  box-shadow: 0 4px 12px rgba(var(--color-accent-rgb, 200, 218, 43), 0.3);
  
  &:active {
    opacity: 0.9;
  }
}
</style>
