<template>
  <view v-if="authStore.isLoggedIn" class="page bg-paper min-h-screen pb-12">
    <!-- 头像（居中大图） -->
    <!-- #ifdef MP-WEIXIN -->
    <button
      class="avatar-btn"
      open-type="chooseAvatar"
      @chooseavatar="onChooseAvatar"
    >
      <image
        v-if="avatarUrl"
        :src="avatarUrl"
        mode="aspectFill"
        class="w-[120rpx] h-[120rpx] rounded-full bg-paper ring-2 ring-lime/70"
      />
      <view
        v-else
        class="w-[120rpx] h-[120rpx] rounded-full bg-lime/20 flex items-center justify-center text-5xl ring-2 ring-lime/70"
      >
        🎾
      </view>
      <text class="text-xs text-olive-light mt-3">点击更换头像</text>
    </button>
    <!-- #endif -->

    <!-- 头像（H5：uni.chooseImage 降级） -->
    <!-- #ifdef H5 -->
    <view class="avatar-btn" @click="handleAvatarChangeH5">
      <image
        v-if="avatarUrl"
        :src="avatarUrl"
        mode="aspectFill"
        class="w-[120rpx] h-[120rpx] rounded-full bg-paper ring-2 ring-lime/70"
      />
      <view
        v-else
        class="w-[120rpx] h-[120rpx] rounded-full bg-lime/20 flex items-center justify-center text-5xl ring-2 ring-lime/70"
      >
        🎾
      </view>
      <text class="text-xs text-olive-light mt-3">点击更换头像</text>
    </view>
    <!-- #endif -->

    <!-- 资料表单（每字段自动保存） -->
    <view class="mx-4 mt-5 bg-white rounded-card overflow-hidden">
      <!-- 昵称 -->
      <view class="flex items-center justify-between px-4 py-3.5">
        <text class="text-sm text-olive shrink-0">昵称</text>
        <input
          class="field-input w-48 text-right"
          type="nickname"
          placeholder="设置昵称"
          placeholder-class="text-olive-light/60"
          :value="nickname"
          :maxlength="24"
          @input="onNicknameInput"
          @blur="saveNickname"
          @confirm="saveNickname"
        />
      </view>
      <view class="h-px bg-paper mx-4"></view>

      <!-- 性别 -->
      <view class="flex items-center justify-between px-4 py-3.5">
        <text class="text-sm text-olive shrink-0">性别</text>
        <picker :value="genderIndex" :range="genderLabels" @change="onGenderChange">
          <view class="flex items-center gap-1">
            <text class="text-sm text-olive-light">{{ genderLabels[genderIndex] }}</text>
            <text class="text-olive-light">›</text>
          </view>
        </picker>
      </view>
      <view class="h-px bg-paper mx-4"></view>

      <!-- 生日 -->
      <view class="flex items-center justify-between px-4 py-3.5">
        <text class="text-sm text-olive shrink-0">生日</text>
        <picker mode="date" :value="birthday" :start="'1900-01-01'" :end="today" @change="onBirthdayChange">
          <view class="flex items-center gap-1">
            <text class="text-sm text-olive-light">{{ birthday || "未设置" }}</text>
            <text class="text-olive-light">›</text>
          </view>
        </picker>
      </view>
    </view>

    <!-- 退出登录 -->
    <view class="mt-10 text-center press-btn" @tap="doLogout">
      <text class="text-sm text-red-500">退出登录</text>
    </view>
  </view>

  <view v-else class="text-center text-sm text-olive-light mt-20">请先登录后再编辑资料</view>
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
const saving = ref(false);
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

function onNicknameInput(e: any) {
  nickname.value = e.detail.value;
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
  saving.value = true;
  try {
    const url = await uploadAvatar(tempUrl);
    avatarUrl.value = resolveUploadUrl(url);
    const result = await updateProfile({ avatar_url: url });
    authStore.updateUser(result.user);
    uni.showToast({ title: "头像已更新", icon: "success" });
  } catch (err: any) {
    uni.showToast({ title: err?.message || "更换失败", icon: "none" });
  } finally {
    saving.value = false;
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
  saving.value = true;
  try {
    const result = await updateProfile(payload);
    authStore.updateUser(result.user);
    uni.showToast({ title: successMsg, icon: "success" });
  } catch (err: any) {
    uni.showToast({ title: err?.message || "保存失败", icon: "none" });
  } finally {
    saving.value = false;
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

<style scoped>
.avatar-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12rpx;
  background: none;
  border: none;
  line-height: normal;
  padding: 32rpx 0 0;
  margin: 0;
  width: 100%;
}

.avatar-btn::after {
  border: none;
}

.press-btn:active {
  opacity: 0.9;
}
</style>
