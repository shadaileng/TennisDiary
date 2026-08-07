<template>
  <view class="page bg-paper min-h-screen pb-12">
    <!-- 用户信息卡（深橄榄渐变 + 青柠光斑） -->
    <view
      class="m-4 mb-3 rounded-hero p-5 overflow-hidden relative bg-gradient-to-br from-olive via-olive-mid to-olive"
      :class="{ 'press-btn': authStore.isLoggedIn }"
      @tap="authStore.isLoggedIn && goEditProfile()"
    >
      <!-- 青柠光斑 -->
      <view class="absolute -top-10 -right-10 w-40 h-40 rounded-full bg-lime/20 blur-2xl"></view>
      <view class="absolute -bottom-16 -left-10 w-44 h-44 rounded-full bg-lime/10 blur-2xl"></view>

      <!-- 用户信息 -->
      <view class="relative flex items-center gap-3">
        <view
          class="w-14 h-14 rounded-full bg-lime flex items-center justify-center text-2xl shrink-0 ring-2 ring-lime/70"
        >
          {{ userAvatar ? "" : "🎾" }}
          <image
            v-if="userAvatar"
            :src="userAvatar"
            mode="aspectFill"
            class="w-14 h-14 rounded-full"
          />
        </view>
        <view class="flex-1 min-w-0">
          <text class="block text-white text-lg font-bold">
            {{ authStore.user?.nickname || "未登录" }}
          </text>
          <text class="block text-white/60 text-xs mt-0.5">
            {{ authStore.user ? `ID ${maskMiddle(authStore.user.id)}` : "登录后可同步日记数据" }}
          </text>
          <text
            v-if="authStore.user"
            class="block text-white/50 text-[11px] mt-0.5"
          >{{ genderLabel }} · {{ birthdayLabel }}</text>
        </view>
        <text v-if="authStore.isLoggedIn" class="text-white/60 text-xl shrink-0">›</text>
      </view>

      <!-- 统计徽章区（登录后拉 /stats） -->
      <view v-if="authStore.isLoggedIn" class="relative mt-4 grid grid-cols-3 gap-2">
        <view class="bg-white/10 rounded-xl py-3 text-center">
          <text class="block text-white text-xl font-bold">{{ stats?.total_sessions ?? 0 }}</text>
          <text class="block text-white/60 text-[11px] mt-0.5">累计打球</text>
        </view>
        <view class="bg-white/10 rounded-xl py-3 text-center">
          <text class="block text-white text-xl font-bold">{{ fmtDuration(stats?.total_duration ?? 0) }}</text>
          <text class="block text-white/60 text-[11px] mt-0.5">累计时长</text>
        </view>
        <view class="bg-white/10 rounded-xl py-3 text-center">
          <text class="block text-white text-xl font-bold">{{ stats?.total_gears ?? 0 }}</text>
          <text class="block text-white/60 text-[11px] mt-0.5">装备</text>
        </view>
      </view>

      <!-- 主按钮：未登录=微信一键登录；已登录=编辑资料 -->
      <view
        v-if="!authStore.isLoggedIn"
        class="relative mt-4 bg-white text-olive text-center text-sm font-medium py-2.5 rounded-full press-btn"
        @tap="doLogin"
      >
        微信一键登录
      </view>
      <view
        v-else
        class="relative mt-4 bg-white text-olive text-center text-sm font-medium py-2.5 rounded-full press-btn"
        @tap="goEditProfile"
      >
        编辑资料
      </view>
    </view>

    <!-- 功能菜单（仅登录后显示） -->
    <view v-if="authStore.isLoggedIn" class="mx-4 bg-white rounded-card overflow-hidden">
      <view
        class="flex items-center px-4 py-3.5 press-btn"
        @tap="goStats"
      >
        <text class="text-base mr-3">📊</text>
        <text class="flex-1 text-sm text-olive">统计总览</text>
        <text class="text-olive-light text-lg">›</text>
      </view>
      <view
        class="flex items-center px-4 py-3.5 border-t border-paper press-btn"
        @tap="goEditProfile"
      >
        <text class="text-base mr-3">⚙️</text>
        <text class="flex-1 text-sm text-olive">编辑资料</text>
        <text class="text-olive-light text-lg">›</text>
      </view>
      <view class="flex items-center justify-between px-4 py-3.5 border-t border-paper">
        <view class="flex items-center">
          <text class="text-base mr-3">💰</text>
          <view>
            <text class="block text-sm text-olive">金额隐私</text>
            <text class="block text-xs text-olive-light mt-0.5">隐藏日记与装备中的具体金额</text>
          </view>
        </view>
        <switch :checked="settingsStore.hideAmounts" color="#A8B822" @change="settingsStore.toggleHideAmounts()" />
      </view>
      <view class="flex items-center justify-between px-4 py-3.5 border-t border-paper">
        <view class="flex items-center">
          <text class="text-base mr-3">🎨</text>
          <view>
            <text class="block text-sm text-olive">青柠主题</text>
            <text class="block text-xs text-olive-light mt-0.5">使用青柠强调色</text>
          </view>
        </view>
        <switch :checked="settingsStore.useLimeTheme" color="#A8B822" @change="settingsStore.toggleLimeTheme()" />
      </view>
    </view>

    <!-- 关于 -->
    <view class="mt-6 text-center px-6">
      <text class="block text-sm text-olive font-medium">Tennis Diary</text>
      <text class="block text-xs text-olive-light mt-1 leading-relaxed">
        结构化记录打球数据 · 体重管理 · 装备库
      </text>
      <text class="block text-[11px] text-olive-light/70 mt-3">v1.0 · 为热爱网球的你而做</text>
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

const authStore = useAuthStore();
const settingsStore = useSettingsStore();

/** 统计徽章数据（登录后拉取，失败静默降级） */
const stats = ref<Stats | null>(null);

/** 头像完整展示 URL */
const userAvatar = computed(() => resolveUploadUrl(authStore.user?.avatar_url || ""));

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
  try {
    stats.value = await getStats();
  } catch {
    stats.value = null;
  }
}

function goStats() {
  uni.switchTab({ url: "/pages/stats/stats" });
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

<style scoped>
.press-btn:active {
  opacity: 0.9;
}
</style>
