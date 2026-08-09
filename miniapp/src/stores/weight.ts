import { defineStore } from "pinia";

import { createWeight, deleteWeight, getWeights } from "@/services/data";
import type { WeightCreate, WeightRecord } from "@/types";
import { createTraceId, logError, logInfo } from "@/utils/eventLogger";

function getCurrentPage(): string {
  try {
    const pages = getCurrentPages();
    return pages[pages.length - 1]?.route || "";
  } catch {
    return "";
  }
}

interface WeightState {
  weights: WeightRecord[]
  loading: boolean
}

/**
 * 体重数据 store
 *
 * 管理体重记录列表，action 对接 /api/weights 接口。
 */
export const useWeightStore = defineStore("weight", {
  state: (): WeightState => ({
    weights: [],
    loading: false,
  }),

  getters: {
    /** 按日期倒序的体重记录（最新在前） */
    sortedWeights: (state): WeightRecord[] =>
      [...state.weights].sort((a, b) => b.date.localeCompare(a.date)),
  },

  actions: {
    setWeights(list: WeightRecord[]) {
      this.weights = list;
    },

    /** 拉取体重记录（GET /api/weights） */
    async fetchList() {
      this.loading = true;
      try {
        this.weights = await getWeights();
      } catch (e) {
        console.error("[weight] 拉取体重记录失败", e);
      } finally {
        this.loading = false;
      }
    },

    /** 添加体重记录（POST /api/weights），成功后插入列表头部 */
    async create(body: WeightCreate): Promise<WeightRecord> {
      const traceId = createTraceId();
      try {
        logInfo("记录体重", { trace_id: traceId, page: getCurrentPage(), date: body.date, weight: body.weight });
        const w = await createWeight(body);
        this.weights = [w, ...this.weights];
        logInfo("体重记录成功", { trace_id: traceId, weight_id: w.id });
        return w;
      } catch (e) {
        logError("体重记录失败", { trace_id: traceId, error: (e as Error).message });
        throw e;
      }
    },

    /** 删除体重记录（DELETE /api/weights/{id}），成功后从列表移除 */
    async remove(id: number) {
      const traceId = createTraceId();
      try {
        logInfo("删除体重记录", { trace_id: traceId, page: getCurrentPage(), weight_id: id });
        await deleteWeight(id);
        this.weights = this.weights.filter((x) => x.id !== id);
        logInfo("体重记录删除成功", { trace_id: traceId, weight_id: id });
      } catch (e) {
        logError("体重记录删除失败", { trace_id: traceId, weight_id: id, error: (e as Error).message });
        throw e;
      }
    },
  },
});
