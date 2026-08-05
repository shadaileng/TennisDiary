import { defineStore } from "pinia";

import type { WeightRecord } from "@/types";

interface WeightState {
  weights: WeightRecord[]
  loading: boolean
}

/**
 * 体重数据 store
 *
 * 管理体重记录列表。Phase1-7 网络层完成后，由 fetchList 对接 /api/weights 接口。
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

    /** 拉取体重记录（Phase1-7 网络层接入后填充实现） */
    async fetchList() {
      // TODO(Phase1-7): GET /api/weights
      this.weights = [];
    },
  },
});
