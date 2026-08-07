<script setup lang="ts">
import { onLaunch, onShow, onHide } from "@dcloudio/uni-app";
import { useAuthStore } from "@/stores/auth";
import { useSettingsStore } from "@/stores/settings";
onLaunch(() => {
  // 恢复持久化的登录态与偏好设置
  const auth = useAuthStore();
  auth.init();
  useSettingsStore().init();
  // 曾登录过才静默登录（wx.login → 换 JWT → 持久化）；首次启动不请求后台
  auth.ensureLogin();
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
@tailwind utilities;
</style>
