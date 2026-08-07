<template>
  <view class="page bg-paper min-h-screen pb-12">
    <view v-if="authStore.isLoggedIn" class="px-4 space-y-3.5 pt-4">
      <!-- 头像 -->
      <view class="bg-white rounded-card p-4">
        <text class="block text-sm font-semibold text-olive mb-3">头像</text>
        <button
          class="avatar-btn"
          open-type="chooseAvatar"
          @chooseavatar="onChooseAvatar"
        >
          <image
            v-if="avatarUrl"
            :src="avatarUrl"
            mode="aspectFill"
            class="w-20 h-20 rounded-full bg-paper"
          />
          <view v-else class="w-20 h-20 rounded-full bg-paper flex items-center justify-center text-3xl">
            🎾
          </view>
          <text class="text-xs text-olive-light">点击更换头像</text>
        </button>
      </view>

      <!-- 资料表单 -->
      <view class="bg-white rounded-card overflow-hidden">
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
          <picker mode="date" :value="birthday" :end="today" @change="onBirthdayChange">
            <view class="flex items-center gap-1">
              <text class="text-sm text-olive-light">{{ birthday || "未设置" }}</text>
              <text class="text-olive-light">›</text>
            </view>
          </picker>
        </view>
      </view>

      <!-- 保存 -->
      <view
        class="bg-olive text-white text-center text-sm font-medium py-3 rounded-full press-btn"
        @tap="onSave"
      >
        保存
      </view>
      <text v-if="saving" class="block text-center text-xs text-olive-light">保存中...</text>
    </view>

    <view v-else class="text-center text-sm text-olive-light mt-20">请先登录后再编辑资料</view>
  </view>
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
  if (!Number.isNaN(idx)) genderIndex.value = idx;
}

function onBirthdayChange(e: any) {
  birthday.value = e.detail.value || "";
}

async function onChooseAvatar(e: any) {
  const tempUrl = e.detail?.avatarUrl;
  if (!tempUrl) return;
  saving.value = true;
  try {
    const url = await uploadAvatar(tempUrl);
    avatarUrl.value = resolveUploadUrl(url);
    const result = await updateProfile({ avatar_url: url });
    authStore.updateUser(result.user);
    uni.showToast({ title: "头像已更新", icon: "success" });
  } catch (err: any) {
    if (err?.errMsg?.includes("cancel")) return;
    uni.showToast({ title: err?.message || "更换失败", icon: "none" });
  } finally {
    saving.value = false;
  }
}

async function onSave() {
  const name = nickname.value.trim();
  if (!name) {
    uni.showToast({ title: "昵称不能为空", icon: "none" });
    return;
  }
  saving.value = true;
  try {
    const result = await updateProfile({
      nickname: name,
      gender: genderIndex.value,
      birthday: birthday.value,
    });
    authStore.updateUser(result.user);
    uni.showToast({ title: "已保存", icon: "success" });
    setTimeout(() => uni.navigateBack(), 500);
  } catch (err: any) {
    uni.showToast({ title: err?.message || "保存失败", icon: "none" });
  } finally {
    saving.value = false;
  }
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
  padding: 0;
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
