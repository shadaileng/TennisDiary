<template>
  <view
    class="cell"
    :class="{ 'cell--press': isLink }"
    @tap="$emit('click')"
  >
    <view class="cell-content">
      <text class="cell-title">{{ title }}</text>
      <text v-if="label" class="cell-label">{{ label }}</text>
    </view>
    <view v-if="value || isLink" class="cell-value">
      <text v-if="value" class="cell-value-text">{{ value }}</text>
      <text v-if="isLink" class="cell-arrow">›</text>
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

<style scoped lang="scss">
@import "@/styles/tokens.scss";

.cell {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: $space-md $space-lg;
  transition: background-color 0.15s ease;
}

.cell--press:active {
  background-color: rgba(0, 0, 0, 0.03);
}

.cell-content {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
}

.cell-title {
  font-size: 14px;
  color: $color-ink;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.cell-label {
  font-size: 12px;
  color: $color-olive-light;
  margin-top: 2px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.cell-value {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-left: $space-sm;
  flex-shrink: 0;
}

.cell-value-text {
  font-size: 14px;
  color: $color-olive-light;
}

.cell-arrow {
  color: $color-olive-light;
  font-size: 14px;
  line-height: 1;
}
</style>
