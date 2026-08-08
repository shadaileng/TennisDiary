<template>
  <view v-if="authStore.isLoggedIn" class="detail-page">
    <!-- 头像（小程序：chooseAvatar 按钮） -->
    <!-- #ifdef MP-WEIXIN -->
    <button class="avatar-section" open-type="chooseAvatar" @chooseavatar="onChooseAvatar">
      <image v-if="avatarUrl" :src="avatarUrl" mode="aspectFill" class="avatar-img" />
      <view v-else class="avatar-placeholder">🎾</view>
      <text class="avatar-hint">点击更换头像</text>
    </button>
    <!-- #endif -->

    <!-- 头像（H5：点击触发 uni.chooseImage） -->
    <!-- #ifdef H5 -->
    <view class="avatar-section" @click="handleAvatarChangeH5">
      <image v-if="avatarUrl" :src="avatarUrl" mode="aspectFill" class="avatar-img" />
      <view v-else class="avatar-placeholder">🎾</view>
      <text class="avatar-hint">点击更换头像</text>
    </view>
    <!-- #endif -->

    <!-- 资料表单（每字段自动保存） -->
    <view class="form-section">
      <!-- 昵称 -->
      <view class="form-row">
        <text class="form-label">昵称</text>
        <input
          v-model="nickname"
          type="nickname"
          class="form-input"
          :maxlength="24"
          placeholder="设置昵称"
          @blur="saveNickname"
          @confirm="saveNickname"
        />
      </view>

      <view class="form-divider"></view>

      <!-- 性别 -->
      <view class="form-row">
        <text class="form-label">性别</text>
        <picker :value="genderIndex" :range="genderLabels" @change="onGenderChange">
          <view class="form-value-row">
            <text class="form-value form-value-clickable">{{ genderLabels[genderIndex] }}</text>
            <text class="form-arrow">›</text>
          </view>
        </picker>
      </view>

      <view class="form-divider"></view>

      <!-- 生日 -->
      <view class="form-row">
        <text class="form-label">生日</text>
        <picker mode="date" :value="birthday" :start="'1900-01-01'" :end="today" @change="onBirthdayChange">
          <view class="form-value-row">
            <text class="form-value form-value-clickable">{{ birthday || "未设置" }}</text>
            <text class="form-arrow">›</text>
          </view>
        </picker>
      </view>
    </view>

    <!-- 退出登录 -->
    <view class="logout-section" @tap="doLogout">
      <text>退出登录</text>
    </view>
  </view>

  <view v-else class="not-login">请先登录后再编辑资料</view>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { onShow } from "@dcloudio/uni-app";

import { uploadAvatar, updateProfile } from "@/services/auth";
import { useAuthStore } from "@/stores";
import { resolveUploadUrl, todayStr } from "@/utils";

const authStore = useAuthStore();

const genderLabels = ["保密", "男", "女"] as const;

const nickname = ref("");
const genderIndex = ref(0);
const birthday = ref("");
const today = todayStr();

/** 用于展示的头像完整 URL（相对路径拼 BASE_URL） */
const avatarUrl = ref("");

onShow(() => {
  if (!authStore.isLoggedIn) return;
  const user = authStore.user;
  nickname.value = user?.nickname || "";
  genderIndex.value = user?.gender ?? 0;
  birthday.value = user?.birthday || "";
  avatarUrl.value = resolveUploadUrl(user?.avatar_url || "");
});

function onGenderChange(e: any) {
  const idx = Number(e.detail.value);
  if (Number.isNaN(idx)) return;
  genderIndex.value = idx;
  saveField({ gender: idx }, "已保存");
}

function onBirthdayChange(e: any) {
  const date = e.detail.value || "";
  birthday.value = date;
  if (!date) return;
  saveField({ birthday: date }, "已保存");
}

async function onChooseAvatar(e: any) {
  const tempUrl = e.detail?.avatarUrl;
  if (!tempUrl) return;
  await uploadAndSaveAvatar(tempUrl);
}

/** H5：uni.chooseImage 降级选择头像 */
async function handleAvatarChangeH5() {
  try {
    const res = await uni.chooseImage({
      count: 1,
      sizeType: ["compressed"],
      sourceType: ["album", "camera"],
    });
    const tempPath = res.tempFilePaths[0];
    if (tempPath) await uploadAndSaveAvatar(tempPath);
  } catch (err: any) {
    if (err?.errMsg?.includes("cancel")) return;
    uni.showToast({ title: err?.message || "更换失败", icon: "none" });
  }
}

async function uploadAndSaveAvatar(tempUrl: string) {
  try {
    const url = await uploadAvatar(tempUrl);
    avatarUrl.value = resolveUploadUrl(url);
    const result = await updateProfile({ avatar_url: url });
    authStore.updateUser(result.user);
    uni.showToast({ title: "头像已更新", icon: "success" });
  } catch (err: any) {
    uni.showToast({ title: err?.message || "更换失败", icon: "none" });
  }
}

/** 昵称失焦保存（空值忽略） */
async function saveNickname() {
  const name = nickname.value.trim();
  if (!name) return;
  await saveField({ nickname: name }, "已保存");
}

/** 通用字段自动保存：调用 updateProfile → 同步本地 user → 轻提示 */
async function saveField(payload: Record<string, unknown>, successMsg: string) {
  try {
    const result = await updateProfile(payload);
    authStore.updateUser(result.user);
    uni.showToast({ title: successMsg, icon: "success" });
  } catch (err: any) {
    uni.showToast({ title: err?.message || "保存失败", icon: "none" });
  }
}

function doLogout() {
  uni.showModal({
    title: "确认退出",
    content: "退出登录后记录仍保留在本地。",
    confirmColor: "#A8B822",
    success: (res) => {
      if (!res.confirm) return;
      authStore.logout();
      uni.showToast({ title: "已退出", icon: "success" });
      setTimeout(() => uni.switchTab({ url: "/pages/mine/mine" }), 300);
    },
  });
}
</script>

<style lang="scss" scoped>
.detail-page {
  min-height: 100vh;
  background: #f2f2ef;
  padding: 32rpx 24rpx;
  padding-bottom: 60rpx;
  box-sizing: border-box;
}

// ========== 头像区域 ==========
.avatar-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 32rpx 0;
  background: none;
  border: none;
  line-height: normal;
  margin: 0;

  &::after {
    border: none;
  }
}

.avatar-img {
  width: 120rpx;
  height: 120rpx;
  border-radius: 50%;
  box-shadow: 0 0 0 4rpx rgba(200, 218, 43, 0.7);
}

.avatar-placeholder {
  width: 120rpx;
  height: 120rpx;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(200, 218, 43, 0.2);
  font-size: 52rpx;
  box-shadow: 0 0 0 4rpx rgba(200, 218, 43, 0.7);
}

.avatar-hint {
  font-size: 24rpx;
  color: #6b7562;
  margin-top: 16rpx;
}

// ========== 表单区域 ==========
.form-section {
  background: #ffffff;
  border-radius: 20rpx;
  padding: 0 32rpx;
  margin-top: 24rpx;
}

.form-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 96rpx;
}

.form-label {
  font-size: 28rpx;
  color: #242b1f;
  flex-shrink: 0;
  font-weight: 500;
}

.form-value-row {
  display: flex;
  align-items: center;
  gap: 8rpx;
}

.form-value {
  font-size: 28rpx;
  color: #6b7562;
}

.form-value-clickable {
  cursor: pointer;
}

.form-input {
  width: 260rpx;
  height: 60rpx;
  background: rgba(0, 0, 0, 0.04);
  border-radius: 12rpx;
  padding: 0 16rpx;
  font-size: 28rpx;
  color: #242b1f;
  text-align: right;
}

.form-arrow {
  font-size: 32rpx;
  color: #6b7562;
}

.form-divider {
  height: 1rpx;
  background: #f2f2ef;
}

// ========== 退出登录 ==========
.logout-section {
  margin-top: 48rpx;
  text-align: center;
  padding: 24rpx 0;

  text {
    font-size: 28rpx;
    color: #e74c3c;
  }
}

.not-login {
  text-align: center;
  font-size: 26rpx;
  color: #6b7562;
  margin-top: 160rpx;
}
</style>
