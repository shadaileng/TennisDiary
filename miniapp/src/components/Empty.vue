<template>
  <view class="empty">
    <text v-if="icon" class="empty-icon">{{ icon }}</text>
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
@import "@/styles/tokens.scss";

.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px $space-lg;
}

.empty-icon {
  font-size: 36px;
  line-height: 1;
  margin-bottom: 12px;
}

.empty-text {
  font-size: 14px;
  color: $color-olive-light;
  text-align: center;
}

.empty-btn {
  margin-top: 16px;
  background-color: $color-olive;
  color: $color-white;
  font-size: 14px;
  font-weight: 500;
  padding: $space-md $space-xl;
  border-radius: 9999px;
  transition: opacity 0.15s ease;
  
  &:active {
    opacity: 0.9;
  }
}
</style>
