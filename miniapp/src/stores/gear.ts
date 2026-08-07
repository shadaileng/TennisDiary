import { defineStore } from "pinia";

import { createGear, deleteGear, getGears, updateGear } from "@/services/data";
import type { Gear, GearCreate, GearUpdate } from "@/types";

interface GearState {
  gears: Gear[]
  loading: boolean
}

/**
 * 装备数据 store
 *
 * 管理装备列表，action 对接 /api/gears 接口。
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

    /** 拉取装备列表（GET /api/gears） */
    async fetchList() {
      this.loading = true;
      try {
        this.gears = await getGears();
      } catch (e) {
        console.error("[gear] 拉取装备列表失败", e);
      } finally {
        this.loading = false;
      }
    },

    /** 添加装备（POST /api/gears），成功后插入列表头部 */
    async create(body: GearCreate): Promise<Gear> {
      const g = await createGear(body);
      this.gears = [g, ...this.gears];
      return g;
    },

    /** 编辑装备（PUT /api/gears/{id}），成功后替换列表项 */
    async update(id: number, body: GearUpdate): Promise<Gear> {
      const g = await updateGear(id, body);
      this.gears = this.gears.map((x) => (x.id === id ? g : x));
      return g;
    },

    /** 删除装备（DELETE /api/gears/{id}），成功后从列表移除 */
    async remove(id: number) {
      await deleteGear(id);
      this.gears = this.gears.filter((x) => x.id !== id);
    },
  },
});
