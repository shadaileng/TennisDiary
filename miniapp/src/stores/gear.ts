import { defineStore } from "pinia";

import type { Gear } from "@/types";

interface GearState {
  gears: Gear[]
  loading: boolean
}

/**
 * 装备数据 store
 *
 * 管理装备列表。Phase1-7 网络层完成后，由 fetchList 对接 /api/gears 接口。
 */
export const useGearStore = defineStore("gear", {
  state: (): GearState => ({
    gears: [],
    loading: false,
  }),

  getters: {
    /** 按种类分组的装备 */
    groupedByCategory: (state): Record<string, Gear[]> => {
      const map: Record<string, Gear[]> = {};
      for (const g of state.gears) {
        const key = g.category || "未分类";
        (map[key] ??= []).push(g);
      }
      return map;
    },
  },

  actions: {
    setGears(list: Gear[]) {
      this.gears = list;
    },

    /** 拉取装备列表（Phase1-7 网络层接入后填充实现） */
    async fetchList() {
      // TODO(Phase1-7): GET /api/gears
      this.gears = [];
    },
  },
});
