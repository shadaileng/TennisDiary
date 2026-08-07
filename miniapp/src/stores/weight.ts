import { defineStore } from "pinia";

import { createWeight, deleteWeight, getWeights } from "@/services/data";
import type { WeightCreate, WeightRecord } from "@/types";

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
      const w = await createWeight(body);
      this.weights = [w, ...this.weights];
      return w;
    },

    /** 删除体重记录（DELETE /api/weights/{id}），成功后从列表移除 */
    async remove(id: number) {
      await deleteWeight(id);
      this.weights = this.weights.filter((x) => x.id !== id);
    },
  },
});
