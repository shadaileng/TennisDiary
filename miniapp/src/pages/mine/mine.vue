<template>
  <view class="page bg-paper min-h-screen pb-12">
    <!-- 用户信息卡（已登录可点击进入编辑资料） -->
    <view
      class="m-4 mb-3 rounded-hero bg-olive p-5 overflow-hidden relative"
      :class="{ 'press-btn': authStore.isLoggedIn }"
      @tap="authStore.isLoggedIn && goEditProfile()"
    >
      <view class="flex items-center gap-3">
        <view class="w-14 h-14 rounded-full bg-lime flex items-center justify-center text-2xl shrink-0">
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

      <!-- 登录 / 登出 / 编辑资料 -->
      <view
        v-if="!authStore.isLoggedIn"
        class="mt-4 bg-white text-olive text-center text-sm font-medium py-2.5 rounded-full press-btn"
        @tap="doLogin"
      >
        微信一键登录
      </view>
      <template v-else>
        <view
          class="mt-4 bg-white text-olive text-center text-sm font-medium py-2.5 rounded-full press-btn"
          @tap="goEditProfile"
        >
          编辑资料
        </view>
        <view
          class="mt-2 bg-white/10 text-white text-center text-sm font-medium py-2.5 rounded-full press-btn"
          @tap="doLogout"
        >
          退出登录
        </view>
      </template>
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
import { computed } from "vue";
import { useAuthStore, useSettingsStore } from "@/stores";
import { maskMiddle, resolveUploadUrl } from "@/utils";

const authStore = useAuthStore();
const settingsStore = useSettingsStore();

/** 头像完整展示 URL */
const userAvatar = computed(() => resolveUploadUrl(authStore.user?.avatar_url || ""));

/** 性别文案 */
const genderLabel = computed(() => {
  const g = authStore.user?.gender;
  return g === 1 ? "男" : g === 2 ? "女" : "保密";
});

/** 生日文案（未设置时隐藏） */
const birthdayLabel = computed(() => (authStore.user?.birthday ? `生日 ${authStore.user.birthday}` : "未设置生日"));

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
