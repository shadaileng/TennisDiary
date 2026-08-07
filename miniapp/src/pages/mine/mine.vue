<template>
  <view class="page bg-paper min-h-screen pb-12">
    <!-- 用户信息卡 -->
    <view class="m-4 mb-3 rounded-hero bg-olive p-5 overflow-hidden relative">
      <view class="flex items-center gap-3">
        <view class="w-14 h-14 rounded-full bg-lime flex items-center justify-center text-2xl shrink-0">
          {{ authStore.user?.avatar_url ? "" : "🎾" }}
          <image
            v-if="authStore.user?.avatar_url"
            :src="authStore.user.avatar_url"
            mode="aspectFill"
            class="w-14 h-14 rounded-full"
          />
        </view>
        <view class="flex-1">
          <text class="block text-white text-lg font-bold">
            {{ authStore.user?.nickname || "未登录" }}
          </text>
          <text class="block text-white/60 text-xs mt-0.5">
            {{ authStore.user ? "已登录" : "登录后可同步日记数据" }}
          </text>
        </view>
      </view>

      <!-- 登录 / 登出 -->
      <view
        v-if="!authStore.isLoggedIn"
        class="mt-4 bg-white text-olive text-center text-sm font-medium py-2.5 rounded-full press-btn"
        @tap="doLogin"
      >
        微信一键登录
      </view>
      <view
        v-else
        class="mt-4 bg-white/10 text-white text-center text-sm font-medium py-2.5 rounded-full press-btn"
        @tap="doLogout"
      >
        退出登录
      </view>
    </view>

    <!-- 设置 -->
    <view class="mx-4 bg-white rounded-card overflow-hidden">
      <view class="flex items-center justify-between px-4 py-3.5">
        <view>
          <text class="block text-sm text-olive">金额隐私</text>
          <text class="block text-xs text-olive-light mt-0.5">隐藏日记与装备中的具体金额</text>
        </view>
        <switch :checked="settingsStore.hideAmounts" color="#A8B822" @change="settingsStore.toggleHideAmounts()" />
      </view>
      <view class="flex items-center justify-between px-4 py-3.5 border-t border-paper">
        <view>
          <text class="block text-sm text-olive">青柠主题</text>
          <text class="block text-xs text-olive-light mt-0.5">使用青柠强调色</text>
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
import { useAuthStore, useSettingsStore } from "@/stores";

const authStore = useAuthStore();
const settingsStore = useSettingsStore();

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

function doLogout() {
  uni.showModal({
    title: "退出登录",
    content: "确定退出当前账号？",
    confirmColor: "#A8B822",
    success: (res) => {
      if (!res.confirm) return;
      authStore.logout();
      uni.showToast({ title: "已退出", icon: "none" });
    },
  });
}
</script>

<style scoped>
.press-btn:active {
  opacity: 0.9;
}
</style>
