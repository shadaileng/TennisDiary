import { defineStore } from "pinia";

import { createWeight, deleteWeight, getWeights } from "@/services/data";
import {
  getPendingWeights,
  upsertPendingWeight,
  removePendingWeight,
  genLocalId,
} from "@/services/pendingRepo";
import { useAuthStore } from "@/stores/auth";
import type { AnyWeight, LocalWeight, WeightCreate, WeightRecord } from "@/types";
import { createTraceId, logError, logInfo } from "@/utils/eventLogger";

function getCurrentPage(): string {
  try {
    const pages = getCurrentPages();
    return pages[pages.length - 1]?.route || "";
  } catch {
    return "";
  }
}

/** 类型守卫：云端体重记录（有数字 id） */
function isCloudWeight(x: AnyWeight): x is WeightRecord {
  return typeof (x as WeightRecord).id === "number";
}

/** 当前是否为游客态 */
function isGuestNow(): boolean {
  return useAuthStore().isGuest;
}

interface WeightState {
  weights: AnyWeight[]
  loading: boolean
}

/**
 * 体重数据 store（Step 129 双路径）
 *
 * 登录态逻辑与现状一致（对接 /api/weights）；游客态读写本地待同步仓库。
 */
export const useWeightStore = defineStore("weight", {
  state: (): WeightState => ({
    weights: [],
    loading: false,
  }),

  getters: {
    /** 按日期倒序的体重记录（最新在前） */
    sortedWeights: (state): AnyWeight[] =>
      [...state.weights].sort((a, b) => b.date.localeCompare(a.date)),
  },

  actions: {
    setWeights(list: AnyWeight[]) {
      this.weights = list;
    },

    /** 拉取体重记录（GET /api/weights）；游客态从本地仓库载入 */
    async fetchList() {
      if (isGuestNow()) {
        this.weights = getPendingWeights();
        return;
      }
      this.loading = true;
      try {
        this.weights = await getWeights();
      } catch (e) {
        logError("体重列表加载失败", { error: (e as Error).message }, undefined, "weight_list_load_failed", undefined, createTraceId());
      } finally {
        this.loading = false;
      }
    },

    /** 添加体重记录：登录态 POST；游客态写入本地仓库 */
    async create(body: WeightCreate): Promise<AnyWeight> {
      if (isGuestNow()) {
        const now = Math.floor(Date.now() / 1000);
        const item: LocalWeight = {
          localId: genLocalId("w"),
          pending: true,
          backendId: null,
          date: body.date,
          weight: body.weight,
          bust: body.bust,
          waist: body.waist,
          hip: body.hip,
          createdAt: now,
        };
        upsertPendingWeight(item);
        this.weights = getPendingWeights();
        return item;
      }
      const traceId = createTraceId();
      try {
        logInfo("记录体重", { trace_id: traceId, date: body.date, weight: body.weight, bust: body.bust, waist: body.waist, hip: body.hip }, undefined, "weight_create", traceId);
        const w = await createWeight(body);
        this.weights = [w, ...this.weights];
        logInfo("体重记录成功", { trace_id: traceId, weight_id: w.id, weight: w.weight }, undefined, "weight_created", traceId);
        return w;
      } catch (e) {
        logError("体重记录失败", { trace_id: traceId, error: (e as Error).message, date: body.date, weight: body.weight }, undefined, "weight_create_failed", undefined, traceId);
        throw e;
      }
    },

    /** 删除体重记录：登录态 DELETE；游客态按 localId 删除本地项 */
    async remove(id: number | string) {
      if (isGuestNow()) {
        removePendingWeight(String(id));
        this.weights = getPendingWeights();
        return;
      }
      const traceId = createTraceId();
      try {
        logInfo("删除体重记录", { trace_id: traceId, weight_id: id }, undefined, "weight_delete", traceId);
        await deleteWeight(id as number);
        this.weights = this.weights.filter((x) => !(isCloudWeight(x) && x.id === id));
        logInfo("体重记录删除成功", { trace_id: traceId, weight_id: id }, undefined, "weight_deleted", traceId);
      } catch (e) {
        logError("体重记录删除失败", { trace_id: traceId, weight_id: id, error: (e as Error).message }, undefined, "weight_delete_failed", undefined, traceId);
        throw e;
      }
    },
  },
});
