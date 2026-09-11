import { defineStore } from "pinia";

import { getAnalyses } from "@/services/data";
import { getAnalysesCache, setAnalysesCache } from "@/services/cloudCache";
import { useAuthStore } from "@/stores/auth";
import { networkOnline } from "@/utils/network";
import type { ApiError } from "@/services/request";
import type { Analysis } from "@/types";
import { createTraceId, logWarn } from "@/utils/eventLogger";

/** 当前登录用户 id（游客/未登录返回 null） */
function currentUserId(): number | null {
  return useAuthStore().user?.id ?? null;
}

interface AnalysisState {
  analyses: Analysis[];
  loading: boolean;
  /** 远端加载失败（网络层 status=-1）后置位：页面据此展示离线横幅 */
  offline: boolean;
  /** 当前列表数据来自本地缓存（未命中云端） */
  fromCache: boolean;
}

/**
 * 电子教练分析列表 store（缓存渲染）
 *
 * 电子教练报告详情体积大、媒体离线无法查看，故仅缓存「列表」：
 * - hydrate：从 cloudCache 立即重建 state，页面可秒开/离线浏览历史列表；
 * - fetchList：仅刷新缓存，网络可用时 GET 拉取并写回缓存，网络失败保持缓存视图并标记离线。
 * 无离线新建场景，故不接 offlineRepo/pendingRepo（与 diary/gear/weight 的差异点）。
 */
export const useAnalysisStore = defineStore("analysis", {
  state: (): AnalysisState => ({
    analyses: [],
    loading: false,
    offline: false,
    fromCache: false,
  }),

  actions: {
    /** 从缓存重建内存态（页面 onShow 先调用 → 立即渲染） */
    hydrate() {
      const uid = currentUserId();
      if (uid == null) {
        this.analyses = [];
        return;
      }
      this.analyses = getAnalysesCache(uid);
      this.fromCache = true;
    },

    /** 拉取分析列表：仅网络可用时 GET 刷新缓存；失败（status=-1）保持缓存视图并置离线标志 */
    async fetchList() {
      const uid = currentUserId();
      if (uid == null) return;
      // 先确保缓存视图已渲染（页面 onShow 已 hydrate；此处兜底）
      this.hydrate();
      if (!networkOnline.value) {
        this.offline = true;
        this.fromCache = true;
        logWarn("分析列表离线（无网络）", { fromCache: true }, undefined, "analysis_list_offline", createTraceId());
        return;
      }
      this.loading = true;
      try {
        const data = await getAnalyses();
        const list = data.items || [];
        setAnalysesCache(uid, list);
        this.analyses = list;
        this.offline = false;
        this.fromCache = false;
      } catch (e) {
        const err = e as ApiError;
        if (err && err.status === -1) {
          // 网络层失败：保持缓存视图，标记离线，不抛错、不清空
          this.offline = true;
          this.fromCache = true;
          logWarn("分析列表加载失败，已降级为缓存视图", { error: err.message }, undefined, "analysis_list_load_failed", createTraceId());
        } else {
          // 业务错误不降级，上抛由页面提示
          this.offline = false;
          throw e;
        }
      } finally {
        this.loading = false;
      }
    },

    /** 删除单条后同步缓存与内存态（避免返回列表需整页重拉） */
    removeAnalysis(id: number) {
      const uid = currentUserId();
      this.analyses = this.analyses.filter((a) => a.id !== id);
      if (uid != null) setAnalysesCache(uid, this.analyses);
    },
  },
});
