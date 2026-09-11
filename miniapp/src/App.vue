<template>
  <Loading />
</template>

<script setup lang="ts">
import { onLaunch, onError } from "@dcloudio/uni-app";
import Loading from "@/components/Loading.vue";
import { useAuthStore } from "@/stores/auth";
import { useSettingsStore } from "@/stores/settings";
import { useCostTagsStore } from "@/stores/costTags";
import { logFatal, logWarn, flushPendingEvents } from "@/utils/eventLogger";
import { networkOnline, probeNetwork } from "@/utils/network";
import { syncOfflineData } from "@/services/sync";

onLaunch(() => {
  // 恢复持久化的登录态与偏好设置；不主动静默登录，未登录即为游客
  const auth = useAuthStore();
  auth.init();
  useSettingsStore().init();
  // 恢复本地费用学习标签候选池
  useCostTagsStore().init();
  // 网络态初始化（Step 141）：探针 + 监听变化，驱动离线横幅/媒体占位/写门禁
  probeNetwork();
  // #ifdef MP-WEIXIN
  uni.onNetworkStatusChange((res) => {
    const online = res.isConnected && res.networkType !== "none";
    networkOnline.value = online;
    // 网络恢复：自动补传账号离线新建（登录态）
    if (online && !useAuthStore().isGuest) {
      syncOfflineData();
    }
  });
  // #endif
  // 启动时补发离线事件
  flushPendingEvents();

  // #ifdef MP-WEIXIN
  // 监听渲染层错误（小程序逻辑层与渲染层分离，onError 仅捕获逻辑层错误）
  wx.onError((errMsg: string) => {
    if (typeof errMsg !== "string" || !errMsg) return;
    // 已知且无危害的降级错误：作为 warn 上报（低打扰），其余按致命错误上报
    if (errMsg.includes("showShareMenu") || errMsg.includes("getPrivacySetting")) {
      logWarn("渲染层已知降级", { errMsg });
      return;
    }
    // nickname 输入在隐私未授权时会静默降级为普通输入（errno:104）：
    // 属预期内交互降级，作为 warn 上报后台，便于追踪但不应掩盖更严重的逻辑错误
    if (errMsg.includes("showNicknameAccessory") || errMsg.includes("nickname")) {
      logWarn("渲染层 nickname 降级", { errMsg });
      return;
    }
    logFatal("渲染层错误", { errMsg });
  });
  // #endif
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
