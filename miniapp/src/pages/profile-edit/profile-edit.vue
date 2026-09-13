<template>
  <page-meta :page-style="themeStyle" :background-color="themeBg" />
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
      <!-- 昵称（微信：点击先请求隐私授权，授权后切换 nickname 输入可弹微信昵称选择） -->
      <view class="form-row">
        <text class="form-label">昵称</text>
        <input
          v-if="!nicknameNickNameEnabled"
          v-model="nickname"
          type="text"
          class="form-input"
          :maxlength="24"
          placeholder="设置昵称"
          @click="ensurePrivacyForNickname"
          @blur="saveNickname"
          @confirm="saveNickname"
        />
        <input
          v-else
          :key="nicknameInputKey"
          ref="nicknameInputRef"
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
import { nextTick, ref } from "vue";
import { onShow } from "@dcloudio/uni-app";

import { uploadAvatar, updateProfile } from "@/services/auth";
import { useThemeStyle } from "@/composables/useTheme";
import { useAuthStore, useSettingsStore } from "@/stores";
import { resolveUploadUrl, todayStr } from "@/utils";
import { createTraceId, logError, logInfo, logWarn } from "@/utils/eventLogger";
import { EV } from "@/utils/eventConstants";
import { checkPrivacySetting, requirePrivacyAuthorize } from "@/utils/privacy";

const authStore = useAuthStore();
const settingsStore = useSettingsStore();
const { themeStyle, themeBg } = useThemeStyle();

const genderLabels = ["保密", "男", "女"] as const;

const nickname = ref("");
const genderIndex = ref(0);
const birthday = ref("");
const today = todayStr();

/** 用于展示的头像完整 URL（相对路径拼 BASE_URL） */
const avatarUrl = ref("");

/** 昵称输入框组件引用（切换为 type="nickname" 后用于聚焦拉起微信昵称选择） */
const nicknameInputRef = ref<any>(null);
/** 昵称输入 key，切换类型时强制重建 input */
const nicknameInputKey = ref(0);
/**
 * 是否已启用微信 nickname 能力（type="nickname"）。
 * 未授权前保持普通 text 输入，避免渲染层 errno:104 降级报错；
 * 授权通过后置 true 重建为 nickname 输入并聚焦以弹出微信昵称选择。
 */
const nicknameNickNameEnabled = ref(false);
/** 是否正在拉起隐私授权（防重入） */
const privacyPrompting = ref(false);
/** 是否已完成过隐私授权引导（授权成功或用户拒绝都算，避免每次点击都弹） */
const privacyAttempted = ref(false);

onShow(() => {
  if (!authStore.isLoggedIn) return;
  const user = authStore.user;
  nickname.value = user?.nickname || "";
  genderIndex.value = user?.gender ?? 0;
  birthday.value = user?.birthday || "";
  avatarUrl.value = resolveUploadUrl(user?.avatar_url || "");
  // 进入页面时恢复普通输入（避免回填后 type=nickname 触发降级）
  nicknameNickNameEnabled.value = false;
  privacyAttempted.value = false;
});

/**
 * 点击昵称输入：未启用 nickname 能力时，在用户手势内请求微信隐私授权。
 * 授权通过 → 重建为 type="nickname" 并聚焦，弹出微信昵称选择面板；
 * 拒绝/低版本 → 保持普通输入，可手动填昵称（一次轻提示）。
 */
async function ensurePrivacyForNickname() {
  // #ifdef MP-WEIXIN
  if (nicknameNickNameEnabled.value || privacyPrompting.value || privacyAttempted.value) return;

  // 已授权（点头像授权过）可直接启用 nickname
  const setting = await checkPrivacySetting();
  if (!setting.needAuthorization) {
    nicknameNickNameEnabled.value = true;
    privacyAttempted.value = true;
    await focusNickName();
    return;
  }

  privacyPrompting.value = true;
  const privacyTraceId = createTraceId();
  logInfo("昵称隐私授权引导", { privacy_contract: setting.privacyContractName }, undefined, EV.PRIVACY_NICKNAME_REQUEST, privacyTraceId);
  try {
    const granted = await requirePrivacyAuthorize();
    if (granted) {
      nicknameNickNameEnabled.value = true;
      privacyAttempted.value = true;
      logInfo("昵称隐私授权通过", undefined, undefined, EV.PRIVACY_NICKNAME_AGREE, privacyTraceId);
      await focusNickName();
    } else {
      privacyAttempted.value = true;
      logWarn("昵称隐私授权被拒，使用手动输入", undefined, "business", EV.PRIVACY_NICKNAME_DENIED, privacyTraceId);
      uni.showToast({ title: "未授权隐私，可手动输入昵称", icon: "none" });
    }
  } catch (err: any) {
    privacyAttempted.value = true;
    logWarn("昵称隐私授权异常", { error: err?.message }, "business", EV.PRIVACY_NICKNAME_ERROR, privacyTraceId);
  } finally {
    privacyPrompting.value = false;
  }
  // #endif
}

/** 切换为 nickname 输入后聚焦以弹出微信昵称选择 */
async function focusNickName() {
  nicknameInputKey.value += 1;
  await nextTick();
  const input = nicknameInputRef.value;
  if (input && typeof input.focus === "function") {
    input.focus();
  }
}

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
  const traceId = createTraceId();
  const t0 = Date.now();

  logInfo("头像更新开始", { has_old: !!authStore.user?.avatar_url }, undefined, EV.AVATAR_UPDATE_START, traceId);

  // 端点1: 上传头像文件
  logInfo("头像上传开始", { temp_url: tempUrl.slice(-20) }, undefined, EV.AVATAR_UPLOAD_START, traceId);
  const tUpload = Date.now();
  let url: string;
  try {
    url = await uploadAvatar(tempUrl);
    logInfo("头像上传成功", {
      duration_ms: Date.now() - tUpload, avatar_url: url,
    }, undefined, EV.AVATAR_UPLOAD_SUCCESS, traceId);
  } catch (err: any) {
    logError("头像上传失败", {
      duration_ms: Date.now() - tUpload, error: err?.message,
    }, undefined, EV.AVATAR_UPLOAD_FAILED, undefined, traceId);
    throw err;
  }

  // 端点2: 保存头像URL到用户资料
  logInfo("保存头像资料开始", { url_length: url.length }, undefined, EV.PROFILE_SAVE_AVATAR_START, traceId);
  const tSave = Date.now();
  try {
    avatarUrl.value = resolveUploadUrl(url);
    const result = await updateProfile({ avatar_url: url });
    authStore.updateUser(result.user);
    logInfo("保存头像资料成功", {
      duration_ms: Date.now() - tSave,
    }, undefined, EV.PROFILE_SAVE_AVATAR_SUCCESS, traceId);
  } catch (err: any) {
    logError("保存头像资料失败", {
      duration_ms: Date.now() - tSave, error: err?.message,
    }, undefined, EV.PROFILE_SAVE_AVATAR_FAILED, undefined, traceId);
    throw err;
  }

  // 整体成功
  logInfo("头像更新完成", {
    total_duration_ms: Date.now() - t0,
  }, undefined, EV.AVATAR_UPDATE_COMPLETE, traceId);
  uni.showToast({ title: "头像已更新", icon: "success" });
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
  const traceId = createTraceId();
  logInfo("准备退出登录", { }, undefined, EV.LOGOUT_START, traceId);
  uni.showModal({
    title: "确认退出",
    content: "退出登录后记录仍保留在本地。",
    confirmColor: settingsStore.themePalette.dark,
    success: (res) => {
      if (!res.confirm) return;
      authStore.logout();
      logInfo("退出登录成功", { }, undefined, EV.LOGOUT, traceId);
      uni.showToast({ title: "已退出", icon: "success" });
      setTimeout(() => uni.switchTab({ url: "/pages/mine/mine" }), 300);
    },
  });
}
</script>

<style lang="scss" scoped>
.detail-page {
  min-height: 100vh;
  background: var(--color-page-bg, #F2F2EF);
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
  box-shadow: 0 0 0 4rpx rgba(var(--color-accent-rgb, 200, 218, 43), 0.7);
}

.avatar-placeholder {
  width: 120rpx;
  height: 120rpx;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(var(--color-accent-rgb, 200, 218, 43), 0.2);
  font-size: 52rpx;
  box-shadow: 0 0 0 4rpx rgba(var(--color-accent-rgb, 200, 218, 43), 0.7);
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
  background: var(--color-page-bg, #F2F2EF);
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
