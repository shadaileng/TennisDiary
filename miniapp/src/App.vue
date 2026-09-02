<template>
  <Loading />
</template>

<script setup lang="ts">
import { onLaunch, onShow, onHide, onError } from "@dcloudio/uni-app";
import Loading from "@/components/Loading.vue";
import { useAuthStore } from "@/stores/auth";
import { useSettingsStore } from "@/stores/settings";
import { logFatal, flushPendingEvents } from "@/utils/eventLogger";

onLaunch(() => {
  // 恢复持久化的登录态与偏好设置；不主动静默登录，未登录即为游客
  const auth = useAuthStore();
  auth.init();
  useSettingsStore().init();
  // 启动时补发离线事件
  flushPendingEvents();
  console.log("App Launch");

  // #ifdef MP-WEIXIN
  // 监听渲染层错误（小程序逻辑层与渲染层分离，onError 仅捕获逻辑层错误）
  wx.onError((errMsg: string) => {
    // 过滤已知的非关键错误
    if (typeof errMsg === "string" &&
        (errMsg.includes("showNicknameAccessory") ||
         errMsg.includes("nickname") ||
         errMsg.includes("showShareMenu") ||
         errMsg.includes("getPrivacySetting"))) {
      return;
    }
    logFatal("渲染层错误", { errMsg });
  });
  // #endif
});
onShow(() => {
  console.log("App Show");
});
onHide(() => {
  console.log("App Hide");
});

// 全局错误捕获
onError((err: any) => {
  const msg = typeof err === "string" ? err : (err?.message || JSON.stringify(err));
  logFatal("全局未捕获错误", { errMsg: msg });
});
</script>
<style>
/* 引入独立 Tailwind 样式入口（对齐 tarot 集成方式，非 scoped） */
@import '@/app.css';
</style>
