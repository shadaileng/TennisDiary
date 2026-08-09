<script setup lang="ts">
import { onLaunch, onShow, onHide, onError } from "@dcloudio/uni-app";
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
