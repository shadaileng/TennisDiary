<template>
  <view v-if="show" class="action-sheet-overlay">
    <!-- 遮罩 -->
    <view class="action-sheet-mask" @tap="$emit('update:show', false)" />
    <!-- 选项列表 -->
    <view class="action-sheet-content">
      <text v-if="title" class="action-sheet-title">{{ title }}</text>
      <view class="action-sheet-list">
        <view
          v-for="(item, index) in actions"
          :key="index"
          class="action-sheet-item"
          :class="index > 0 ? 'action-sheet-item--bordered' : ''"
          :style="{ color: item.color || '#242B1F' }"
          @tap="onSelect(item)"
        >
          {{ item.name }}
        </view>
      </view>
      <view
        class="action-sheet-cancel"
        @tap="$emit('update:show', false)"
      >
        取消
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
export interface ActionSheetAction {
  /** 显示文案 */
  name: string
  /** 返回值 */
  value: string | number
  /** 文字颜色 */
  color?: string
}

withDefaults(
  defineProps<{
    /** 是否显示 */
    show: boolean
    /** 选项列表 */
    actions: ActionSheetAction[]
    /** 标题 */
    title?: string
  }>(),
  {
    show: false,
    title: "",
  },
);

const emit = defineEmits<{
  (e: "update:show", value: boolean): void
  (e: "select", value: ActionSheetAction): void
}>();

function onSelect(item: ActionSheetAction) {
  emit("select", item);
  emit("update:show", false);
}
</script>

<style scoped lang="scss">

.action-sheet-overlay {
  position: fixed;
  inset: 0;
  z-index: 50;
}

.action-sheet-mask {
  position: absolute;
  inset: 0;
  background-color: rgba(0, 0, 0, 0.4);
}

.action-sheet-content {
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

.action-sheet-title {
  display: block;
  text-align: center;
  font-size: 14px;
  color: $color-olive-light;
  margin-bottom: $space-md;
}

.action-sheet-list {
  display: flex;
  flex-direction: column;
}

.action-sheet-item {
  padding: 12px 0;
  text-align: center;
  font-size: 16px;
  transition: opacity 0.15s ease;
  
  &--bordered {
    border-top: 1px solid var(--color-border, #E7E9DF);
  }
  
  &:active {
    opacity: 0.7;
  }
}

.action-sheet-cancel {
  margin-top: 12px;
  padding: 12px 0;
  text-align: center;
  font-size: 14px;
  color: $color-olive-light;
  border-top: 1px solid var(--color-border, #E7E9DF);
}
</style>
