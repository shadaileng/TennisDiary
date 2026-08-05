<template>
  <view class="page">
    <view class="placeholder">
      <text class="icon">🎾</text>
      <text class="title">装备</text>
      <text class="desc">管理球拍等装备，开发中</text>
    </view>
  </view>
</template>

<script setup lang="ts">
</script>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background-color: #f2f2ef;
}
.placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  gap: 16rpx;
  color: #6b7562;
}
.icon {
  font-size: 96rpx;
}
.title {
  font-size: 40rpx;
  font-weight: 600;
  color: #242b1f;
}
.desc {
  font-size: 28rpx;
  color: #6b7562;
}
</style>
