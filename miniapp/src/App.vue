<script setup lang="ts">
import { onLaunch, onShow, onHide } from "@dcloudio/uni-app";
import { useAuthStore } from "@/stores/auth";
import { useSettingsStore } from "@/stores/settings";
onLaunch(() => {
  // 恢复持久化的登录态与偏好设置；不主动静默登录，未登录即为游客
  const auth = useAuthStore();
  auth.init();
  useSettingsStore().init();
  console.log("App Launch");
});
onShow(() => {
  console.log("App Show");
});
onHide(() => {
  console.log("App Hide");
});
</script>
<style>
/* 引入独立 Tailwind 样式入口（对齐 tarot 集成方式，非 scoped） */
@import '@/app.css';
</style>
