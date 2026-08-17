<template>
  <view class="mine-page">
    <!-- 用户信息卡（深橄榄渐变 + 青柠光斑） -->
    <view class="profile-card">
      <view class="profile-header">
        <view class="profile-avatar">
          <image
            v-if="userAvatar"
            :src="userAvatar"
            mode="aspectFill"
            class="avatar-img"
          />
          <text v-else class="avatar-placeholder">🎾</text>
        </view>

        <view class="profile-info">
          <text class="profile-nickname">{{ profileName }}</text>
          <text class="profile-sub">{{ authStore.user ? `ID ${maskMiddle(authStore.user.id)}` : "登录后可同步日记数据" }}</text>
          <text v-if="authStore.user" class="profile-meta">{{ genderLabel }} · {{ birthdayLabel }}</text>
        </view>

        <text v-if="authStore.isLoggedIn" class="profile-arrow" @tap="goEditProfile">›</text>
      </view>

      <!-- 统计徽章区（登录后拉 /stats） -->
      <view v-if="authStore.isLoggedIn" class="stats-row">
        <view class="stat-item">
          <text class="stat-value">{{ stats?.total_sessions ?? 0 }}</text>
          <text class="stat-label">累计打球</text>
        </view>
        <view class="stat-item">
          <text class="stat-value">{{ fmtDuration(stats?.total_duration ?? 0) }}</text>
          <text class="stat-label">累计时长</text>
        </view>
        <view class="stat-item">
          <text class="stat-value">{{ stats?.total_gears ?? 0 }}</text>
          <text class="stat-label">装备</text>
        </view>
      </view>

      <!-- 主按钮：未登录=微信一键登录；已登录=编辑资料 -->
      <view v-if="!authStore.isLoggedIn" class="primary-btn" @tap="doLogin">微信一键登录</view>
      <view v-else class="primary-btn" @tap.stop="goEditProfile">编辑资料</view>
    </view>

    <!-- 功能入口（仅登录后显示） -->
    <view v-if="authStore.isLoggedIn" class="menu-section">
      <view class="menu-item" @tap="goStats">
        <text class="menu-icon">📊</text>
        <text class="menu-label">统计总览</text>
        <text class="menu-arrow">›</text>
      </view>
      <view class="menu-item" @tap="goCoach">
        <text class="menu-icon">🎾</text>
        <text class="menu-label">电子教练</text>
        <text class="menu-arrow">›</text>
      </view>
      <view class="menu-item" @tap="goShare">
        <text class="menu-icon">📤</text>
        <text class="menu-label">分享工坊</text>
        <text class="menu-arrow">›</text>
      </view>
      <view class="menu-item">
        <text class="menu-icon">💰</text>
        <view class="menu-content">
          <text class="menu-label">金额隐私</text>
          <text class="menu-desc">隐藏日记与装备中的具体金额</text>
        </view>
        <switch :checked="settingsStore.hideAmounts" color="#A8B822" @change="settingsStore.toggleHideAmounts()" />
      </view>
      <view class="menu-item">
        <text class="menu-icon">🎨</text>
        <view class="menu-content">
          <text class="menu-label">青柠主题</text>
          <text class="menu-desc">使用青柠强调色</text>
        </view>
        <switch :checked="settingsStore.useLimeTheme" color="#A8B822" @change="settingsStore.toggleLimeTheme()" />
      </view>
    </view>

    <!-- 关于 -->
    <view class="about">
      <text class="about-title">Tennis Diary</text>
      <text class="about-desc">结构化记录打球数据 · 体重管理 · 装备库</text>
      <text class="about-ver">v1.0 · 为热爱网球的你而做</text>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { onShow } from "@dcloudio/uni-app";

import { getStats } from "@/services/data";
import { useAuthStore, useSettingsStore } from "@/stores";
import type { Stats } from "@/types";
import { fmtDuration, maskMiddle, resolveUploadUrl } from "@/utils";
import { createTraceId, logError, logInfo } from "@/utils/eventLogger";

const authStore = useAuthStore();
const settingsStore = useSettingsStore();

/** 统计徽章数据（登录后拉取，失败静默降级） */
const stats = ref<Stats | null>(null);

/** 头像完整展示 URL */
const userAvatar = computed(() => resolveUploadUrl(authStore.user?.avatar_url || ""));

/** 昵称：未登录显示「未登录」；已登录但未设置昵称显示「微信用户」 */
const profileName = computed(() => {
  if (!authStore.isLoggedIn || !authStore.user) return "未登录";
  return authStore.user.nickname || "微信用户";
});

/** 性别文案 */
const genderLabel = computed(() => {
  const g = authStore.user?.gender;
  return g === 1 ? "男" : g === 2 ? "女" : "保密";
});

/** 生日文案（未设置时隐藏） */
const birthdayLabel = computed(() => (authStore.user?.birthday ? `生日 ${authStore.user.birthday}` : "未设置生日"));

onShow(() => {
  if (authStore.isLoggedIn) {
    loadStats();
  } else {
    stats.value = null;
  }
});

/** 拉取统计数据，失败静默降级为 0，不阻塞页面 */
async function loadStats() {
  const traceId = createTraceId();
  logInfo("加载统计总览", { trace_id: traceId }, "mine_stats_load", traceId);
  try {
    stats.value = await getStats();
    logInfo("统计总览加载成功", { trace_id: traceId }, "mine_stats_loaded", traceId);
  } catch (e) {
    stats.value = null;
    logError("统计总览加载失败", { trace_id: traceId, error: (e as Error).message }, "mine_stats_load_failed", undefined, traceId);
  }
}

function goStats() {
  uni.switchTab({ url: "/pages/stats/stats" });
}

function goCoach() {
  uni.navigateTo({ url: "/pages/coach/coach" });
}

function goShare() {
  uni.navigateTo({ url: "/pages/share/share" });
}

function goEditProfile() {
  uni.navigateTo({ url: "/pages/profile-edit/profile-edit" });
}

async function doLogin() {
  uni.showLoading({ title: "登录中", mask: true });
  try {
    await authStore.login();
    uni.hideLoading();
    uni.showToast({ title: "登录成功", icon: "success" });
  } catch (e) {
    uni.hideLoading();
    const msg = e instanceof Error ? e.message : "登录失败";
    uni.showToast({ title: msg, icon: "none" });
  }
}
</script>

<style lang="scss" scoped>
// ========== 页面 ==========
.mine-page {
  min-height: 100vh;
  background: #f2f2ef;
  padding: 24rpx;
  padding-bottom: 40rpx;
  box-sizing: border-box;
}

// ========== 用户信息卡 ==========
.profile-card {
  background: linear-gradient(135deg, #242b1f, #3a4433);
  border-radius: 28rpx;
  padding: 32rpx;
  margin-bottom: 24rpx;
  position: relative;
  overflow: hidden;

  // 青柠光斑
  &::before {
    content: "";
    position: absolute;
    top: -80rpx;
    right: -80rpx;
    width: 260rpx;
    height: 260rpx;
    border-radius: 50%;
    background: rgba(200, 218, 43, 0.2);
    filter: blur(40rpx);
  }
  &::after {
    content: "";
    position: absolute;
    bottom: -120rpx;
    left: -80rpx;
    width: 300rpx;
    height: 300rpx;
    border-radius: 50%;
    background: rgba(200, 218, 43, 0.12);
    filter: blur(50rpx);
  }

  &.clickable {
    cursor: pointer;
  }
}

.profile-header {
  display: flex;
  align-items: center;
  gap: 20rpx;
  position: relative;
  z-index: 1;
}

.profile-avatar {
  width: 88rpx;
  height: 88rpx;
  border-radius: 50%;
  flex-shrink: 0;
  background: #c8da2b;
  overflow: hidden;
  box-shadow: 0 0 0 4rpx rgba(200, 218, 43, 0.7);
}

.avatar-img {
  width: 100%;
  height: 100%;
}

.avatar-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 40rpx;
}

.profile-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 6rpx;
}

.profile-nickname {
  font-size: 32rpx;
  font-weight: 700;
  color: #ffffff;
}

.profile-sub {
  font-size: 22rpx;
  color: rgba(255, 255, 255, 0.6);
}

.profile-meta {
  font-size: 20rpx;
  color: rgba(255, 255, 255, 0.5);
}

.profile-arrow {
  font-size: 44rpx;
  color: rgba(255, 255, 255, 0.6);
  flex-shrink: 0;
  padding: 0 8rpx;
}

// ========== 统计徽章区 ==========
.stats-row {
  display: flex;
  gap: 16rpx;
  margin-top: 32rpx;
  position: relative;
  z-index: 1;
}

.stat-item {
  flex: 1;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 16rpx;
  padding: 20rpx 0;
  text-align: center;
}

.stat-value {
  display: block;
  font-size: 34rpx;
  font-weight: 700;
  color: #ffffff;
}

.stat-label {
  display: block;
  font-size: 20rpx;
  color: rgba(255, 255, 255, 0.6);
  margin-top: 4rpx;
}

// ========== 主按钮 ==========
.primary-btn {
  margin-top: 32rpx;
  background: #ffffff;
  color: #242b1f;
  text-align: center;
  font-size: 26rpx;
  font-weight: 500;
  line-height: 80rpx;
  height: 80rpx;
  border-radius: 40rpx;
  position: relative;
  z-index: 1;
}

// ========== 功能入口 ==========
.menu-section {
  margin-bottom: 24rpx;
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 16rpx;
  background: #ffffff;
  border-radius: 20rpx;
  padding: 24rpx 28rpx;
  margin-bottom: 12rpx;
  cursor: pointer;
}

.menu-icon {
  font-size: 32rpx;
  flex-shrink: 0;
}

.menu-content {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4rpx;
}

.menu-label {
  flex: 1;
  font-size: 26rpx;
  color: #242b1f;
  font-weight: 500;
}

.menu-desc {
  font-size: 20rpx;
  color: #6b7562;
}

.menu-arrow {
  font-size: 36rpx;
  color: #6b7562;
  flex-shrink: 0;
}

// ========== 关于 ==========
.about {
  text-align: center;
  padding: 32rpx 40rpx;
}

.about-title {
  display: block;
  font-size: 28rpx;
  color: #242b1f;
  font-weight: 500;
}

.about-desc {
  display: block;
  font-size: 22rpx;
  color: #6b7562;
  margin-top: 8rpx;
  line-height: 1.6;
}

.about-ver {
  display: block;
  font-size: 20rpx;
  color: rgba(107, 117, 98, 0.7);
  margin-top: 16rpx;
}
</style>
