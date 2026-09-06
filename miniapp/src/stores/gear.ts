import { defineStore } from "pinia";

import { createGear, deleteGear, getGears, updateGear } from "@/services/data";
import {
  getPendingGears,
  upsertPendingGear,
  updatePendingGear,
  removePendingGear,
  genLocalId,
} from "@/services/pendingRepo";
import { useAuthStore } from "@/stores/auth";
import type { AnyGear, Gear, GearCreate, GearUpdate, LocalGear } from "@/types";
import { createTraceId, logError, logInfo } from "@/utils/eventLogger";
import { todayStr } from "@/utils";

function getCurrentPage(): string {
  try {
    const pages = getCurrentPages();
    return pages[pages.length - 1]?.route || "";
  } catch {
    return "";
  }
}

/** 类型守卫：云端装备（有数字 id） */
function isCloudGear(x: AnyGear): x is Gear {
  return typeof (x as Gear).id === "number";
}

/** 当前是否为游客态 */
function isGuestNow(): boolean {
  return useAuthStore().isGuest;
}

interface GearState {
  gears: AnyGear[]
  loading: boolean
}

/**
 * 装备数据 store（Step 129 双路径）
 *
 * 登录态逻辑与现状一致（对接 /api/gears）；游客态读写本地待同步仓库。
 * 日志收敛：不再打印 photo/dataURL 大字段。
 */
export const useGearStore = defineStore("gear", {
  state: (): GearState => ({
    gears: [],
    loading: false,
  }),

  getters: {
    /** 按种类分组的装备 */
    groupedByCategory: (state): Record<string, AnyGear[]> => {
      const map: Record<string, AnyGear[]> = {};
      for (const g of state.gears) {
        const key = g.category || "未分类";
        (map[key] ??= []).push(g);
      }
      return map;
    },
  },

  actions: {
    setGears(list: AnyGear[]) {
      this.gears = list;
    },

    /** 取单条本地待同步装备（游客态编辑回填） */
    getLocalGear(localId: string): LocalGear | undefined {
      return getPendingGears().find((g) => g.localId === localId);
    },

    /** 拉取装备列表（GET /api/gears）；游客态从本地仓库载入 */
    async fetchList() {
      if (isGuestNow()) {
        this.gears = getPendingGears();
        return;
      }
      this.loading = true;
      try {
        this.gears = await getGears();
      } catch (e) {
        logError("装备列表加载失败", { error: (e as Error).message }, undefined, "gear_list_load_failed", undefined, createTraceId());
      } finally {
        this.loading = false;
      }
    },

    /** 添加装备：登录态 POST；游客态写入本地仓库（封面 dataURL） */
    async create(body: GearCreate): Promise<AnyGear> {
      if (isGuestNow()) {
        const now = Math.floor(Date.now() / 1000);
        const item: LocalGear = {
          localId: genLocalId("g"),
          pending: true,
          backendId: null,
          category: body.category || "",
          name: body.name || "",
          buy_date: body.buy_date || todayStr(),
          price: body.price || 0,
          feeling: body.feeling || "",
          photo: body.photo || "",
          createdAt: now,
          business_time: now,
        };
        const saved = upsertPendingGear(item);
        if (!saved) {
          throw new Error("本地保存失败，请尝试登录后同步到云端");
        }
        this.gears = getPendingGears();
        return item;
      }
      const traceId = createTraceId();
      try {
        logInfo("添加装备", { trace_id: traceId, category: body.category, name: body.name, buy_date: body.buy_date, price: body.price, feeling: body.feeling }, undefined, "gear_create", traceId);
        const g = await createGear(body);
        this.gears = [g, ...this.gears];
        logInfo("装备添加成功", { trace_id: traceId, gear_id: g.id, category: g.category, name: g.name }, undefined, "gear_created", traceId);
        return g;
      } catch (e) {
        logError("装备添加失败", { trace_id: traceId, error: (e as Error).message, category: body.category, name: body.name }, undefined, "gear_create_failed", undefined, traceId);
        throw e;
      }
    },

    /** 编辑装备：登录态 PUT；游客态按 localId 更新本地项 */
    async update(id: number | string, body: GearUpdate): Promise<AnyGear> {
      if (isGuestNow()) {
        const saved = updatePendingGear(String(id), body as Partial<LocalGear>);
        if (!saved) {
          throw new Error("本地保存失败，请尝试登录后同步到云端");
        }
        this.gears = getPendingGears();
        return this.gears.find((x) => (x as LocalGear).localId === String(id))!;
      }
      const traceId = createTraceId();
      try {
        logInfo("编辑装备", { trace_id: traceId, gear_id: id, category: body.category, name: body.name, buy_date: body.buy_date, price: body.price, feeling: body.feeling }, undefined, "gear_update", traceId);
        const g = await updateGear(id as number, body);
        this.gears = this.gears.map((x) => (isCloudGear(x) && x.id === id ? g : x));
        logInfo("装备更新成功", { trace_id: traceId, gear_id: id, category: g.category, name: g.name }, undefined, "gear_updated", traceId);
        return g;
      } catch (e) {
        logError("装备更新失败", { trace_id: traceId, gear_id: id, error: (e as Error).message, category: body.category, name: body.name }, undefined, "gear_update_failed", undefined, traceId);
        throw e;
      }
    },

    /** 删除装备：登录态 DELETE；游客态按 localId 删除本地项 */
    async remove(id: number | string) {
      if (isGuestNow()) {
        const removed = removePendingGear(String(id));
        if (!removed) {
          throw new Error("本地删除失败，请重试");
        }
        this.gears = getPendingGears();
        return;
      }
      const traceId = createTraceId();
      try {
        logInfo("删除装备", { trace_id: traceId, gear_id: id }, undefined, "gear_delete", traceId);
        await deleteGear(id as number);
        this.gears = this.gears.filter((x) => !(isCloudGear(x) && x.id === id));
        logInfo("装备删除成功", { trace_id: traceId, gear_id: id }, undefined, "gear_deleted", traceId);
      } catch (e) {
        logError("装备删除失败", { trace_id: traceId, gear_id: id, error: (e as Error).message }, undefined, "gear_delete_failed", undefined, traceId);
        throw e;
      }
    },
  },
});
