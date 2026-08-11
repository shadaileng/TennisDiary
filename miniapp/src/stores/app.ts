import { defineStore } from "pinia";
import { ref } from "vue";

/**
 * 全局应用状态 store
 *
 * Phase 69：全局 Loading 遮罩状态（对齐 Admin 端 Phase 68）。
 * 由 request.ts 的请求计数器控制，页面无需直接调用。
 */
export const useAppStore = defineStore("app", () => {
  const loading = ref(false);

  function setLoading(val: boolean) {
    loading.value = val;
  }

  return { loading, setLoading };
});
