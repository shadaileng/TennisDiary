/**
 * 全局网络可用状态（Step 141）
 *
 * 单一真源：由 App.vue 在 onLaunch 调用 `probeNetwork()` 初始化，
 * 并监听 `uni.onNetworkStatusChange` 维护。供列表横幅、媒体占位、
 * 写操作门禁、自动同步共享，避免各页各自探测。
 */

import { ref } from "vue";

/** 网络是否可用（none 视为不可用） */
export const networkOnline = ref(true);

/** 初始探测当前网络类型，非 none 视为可用 */
export function probeNetwork(): void {
  // #ifdef MP-WEIXIN
  uni.getNetworkType({
    success: (res) => {
      networkOnline.value = res.networkType !== "none";
    },
    fail: () => {
      networkOnline.value = true;
    },
  });
  // #endif
}
