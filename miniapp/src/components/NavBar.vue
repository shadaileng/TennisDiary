<template>
  <view class="nav-bar">
    <view class="nav-bar-content">
      <!-- 左侧：返回或占位 -->
      <view class="nav-bar-back">
        <text
          v-if="showBack"
          class="nav-bar-back-btn"
          @tap="$emit('back')"
        >‹</text>
      </view>

      <!-- 标题 -->
      <text class="nav-bar-title">
        {{ title }}
      </text>

      <!-- 右侧操作 -->
      <view class="nav-bar-right">
        <text
          v-if="rightText"
          class="nav-bar-right-btn"
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

<style scoped lang="scss">

.nav-bar {
  position: sticky;
  top: 0;
  z-index: 10;
  background-color: rgba(242, 242, 239, 0.95);
}

.nav-bar-content {
  display: flex;
  align-items: center;
  height: 48px;
  padding: 0 $space-lg;
}

.nav-bar-back {
  width: 40px;
}

.nav-bar-back-btn {
  font-size: 20px;
  color: $color-ink;
  line-height: 1;
}

.nav-bar-title {
  flex: 1;
  text-align: center;
  font-size: 14px;
  font-weight: 600;
  color: $color-ink;
}

.nav-bar-right {
  width: 40px;
  display: flex;
  justify-content: flex-end;
}

.nav-bar-right-btn {
  font-size: 14px;
  color: $color-lime-dark;
  font-weight: 500;
}
</style>
