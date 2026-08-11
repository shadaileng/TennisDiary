<template>
  <view v-if="loading" class="loading-mask">
    <view class="loading-card">
      <view class="loading-spinner" />
      <text class="loading-text">加载中...</text>
    </view>
  </view>
</template>

<script setup lang="ts">
import { storeToRefs } from "pinia";
import { useAppStore } from "@/stores/app";

/**
 * 全局 Loading 遮罩组件
 *
 * Phase 69：基于 app store 的 loading 状态渲染全屏遮罩，
 * 由 request.ts 请求计数器自动控制，页面无需手动开关。
 */
const { loading } = storeToRefs(useAppStore());
</script>

<style scoped lang="scss">
.loading-mask {
  position: fixed;
  inset: 0;
  z-index: 999;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: rgba(242, 242, 239, 0.6);
}

.loading-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: $space-md;
  padding: $space-xl $space-3xl;
  background-color: $color-white;
  border-radius: $radius-card;
  box-shadow: $shadow-card-md;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 4px solid $color-lime-soft;
  border-top-color: $color-lime-dark;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.loading-text {
  font-size: $font-size-sm;
  color: $color-olive-light;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>
