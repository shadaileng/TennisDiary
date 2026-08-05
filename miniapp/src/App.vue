<script setup lang="ts">
import { onLaunch, onShow, onHide } from "@dcloudio/uni-app";
import { useAuthStore } from "@/stores/auth";
import { useSettingsStore } from "@/stores/settings";
onLaunch(() => {
  // 恢复持久化的登录态与偏好设置
  useAuthStore().init();
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
<style lang="scss">
/* 小程序端只需引入工具类，不需要 base / components */
@import "tailwindcss/utilities";
</style>
