import { defineStore } from "pinia";

import { createGear, deleteGear, getGears, updateGear } from "@/services/data";
import {
  getPendingGears,
  upsertPendingGear,
  updatePendingGear,
  removePendingGear,
  genLocalId,
} from "@/services/pendingRepo";
import { offlineGears } from "@/services/offlineRepo";
import { getCloudGears, setCloudGears } from "@/services/cloudCache";
import { syncOfflineData } from "@/services/sync";
import type { ApiError } from "@/services/request";
import { useAuthStore } from "@/stores/auth";
import { networkOnline } from "@/utils/network";
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

function isGuestNow(): boolean {
  return useAuthStore().isGuest;
}

function currentUserId(): number | null {
  return useAuthStore().user?.id ?? null;
}

/** 构造游客/离线本地装备实体（photo 为本地 dataURL） */
function buildLocalGear(body: GearCreate, now: number): LocalGear {
  return {
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
}

interface GearState {
  gears: AnyGear[]
  loading: boolean
  offline: boolean
  fromCache: boolean
}

/**
 * 装备数据 store（Step 141 缓存合并视图）
 *
 * 同 diary store：渲染源 = merge(cloudCache, offlineRepo)；游客态零改动。
 * 日志收敛：不再打印 photo/dataURL 大字段。
 */
export const useGearStore = defineStore("gear", {
  state: (): GearState => ({
    gears: [],
    loading: false,
    offline: false,
    fromCache: false,
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
    isOffline: (state): boolean => state.offline,
  },

  actions: {
    hydrate() {
      if (isGuestNow()) {
        this.gears = getPendingGears();
        this.offline = false;
        this.fromCache = false;
        return;
      }
      const uid = currentUserId();
      if (uid == null) {
        this.gears = [];
        return;
      }
      this.gears = [...getCloudGears(uid), ...offlineGears.get(uid)];
      this.fromCache = true;
    },

    setGears(list: AnyGear[]) {
      this.gears = list;
    },

    /** 取单条本地待同步装备（游客 / 登录态离线项编辑回填） */
    getLocalGear(localId: string): LocalGear | undefined {
      if (isGuestNow()) {
        return getPendingGears().find((g) => g.localId === localId);
      }
      const uid = currentUserId();
      if (uid != null) {
        const off = offlineGears.get(uid).find((g) => g.localId === localId);
        if (off) return off;
      }
      return getPendingGears().find((g) => g.localId === localId);
    },

    /** 拉取装备列表：登录态仅网络可用时 GET 刷新缓存；失败保持缓存视图 */
    async fetchList() {
      if (isGuestNow()) {
        this.gears = getPendingGears();
        return;
      }
      const uid = currentUserId();
      if (uid == null) return;
      this.hydrate();
      if (!networkOnline.value) {
        this.offline = true;
        this.fromCache = true;
        return;
      }
      this.loading = true;
      try {
        const list = await getGears();
        setCloudGears(uid, list);
        await syncOfflineData();
        this.hydrate();
        this.offline = false;
        this.fromCache = false;
      } catch (e) {
        const err = e as ApiError;
        if (err && err.status === -1) {
          this.offline = true;
          this.fromCache = true;
        } else {
          this.offline = false;
          throw e;
        }
      } finally {
        this.loading = false;
      }
    },

    /** 离线新建：写入 offlineRepo 并刷新合并视图 */
    createOffline(body: GearCreate): LocalGear {
      const uid = currentUserId()!;
      const now = Math.floor(Date.now() / 1000);
      const item = buildLocalGear(body, now);
      offlineGears.upsert(uid, item);
      this.hydrate();
      logInfo("离线新建装备（待同步）", { local_id: item.localId, name: body.name }, undefined, "offline_create_pending", createTraceId());
      return item;
    },

    /** 添加装备：在线成功 → 写缓存；离线/网络失败 → 落 offlineRepo */
    async create(body: GearCreate): Promise<AnyGear> {
      if (isGuestNow()) {
        const now = Math.floor(Date.now() / 1000);
        const item = buildLocalGear(body, now);
        const saved = upsertPendingGear(item);
        if (!saved) throw new Error("本地保存失败，请尝试登录后同步到云端");
        this.gears = getPendingGears();
        return item;
      }
      const uid = currentUserId();
      if (uid == null) throw new Error("未登录");
      if (!networkOnline.value) {
        return this.createOffline(body);
      }
      const traceId = createTraceId();
      try {
        logInfo("添加装备", { trace_id: traceId, name: body.name }, undefined, "gear_create", traceId);
        const g = await createGear(body);
        setCloudGears(uid, [g, ...getCloudGears(uid)]);
        this.hydrate();
        logInfo("装备添加成功", { trace_id: traceId, gear_id: g.id }, undefined, "gear_created", traceId);
        return g;
      } catch (e) {
        const err = e as ApiError;
        if (err && err.status === -1) {
          return this.createOffline(body);
        }
        logError("装备添加失败", { trace_id: traceId, error: err?.message, name: body.name }, undefined, "gear_create_failed", undefined, traceId);
        throw e;
      }
    },

    /** 编辑：本地项纯本地改；云端项在线成功才改缓存视图 */
    async update(id: number | string, body: GearUpdate): Promise<AnyGear> {
      if (isGuestNow()) {
        const saved = updatePendingGear(String(id), body as Partial<LocalGear>);
        if (!saved) throw new Error("本地保存失败，请尝试登录后同步到云端");
        this.gears = getPendingGears();
        return this.gears.find((x) => (x as LocalGear).localId === String(id))!;
      }
      const uid = currentUserId();
      if (uid == null) throw new Error("未登录");
      if (typeof id === "string") {
        const saved = offlineGears.update(uid, id, body as Partial<LocalGear>);
        if (!saved) throw new Error("本地保存失败，请尝试登录后同步到云端");
        this.hydrate();
        return this.gears.find((x) => (x as LocalGear).localId === String(id))!;
      }
      const traceId = createTraceId();
      try {
        logInfo("编辑装备", { trace_id: traceId, gear_id: id }, undefined, "gear_update", traceId);
        const g = await updateGear(id, body);
        setCloudGears(uid, getCloudGears(uid).map((x) => (x.id === id ? g : x)));
        this.hydrate();
        logInfo("装备更新成功", { trace_id: traceId, gear_id: id }, undefined, "gear_updated", traceId);
        return g;
      } catch (e) {
        const err = e as ApiError;
        if (err && err.status === -1) {
          uni.showToast({ title: "网络不可用，请联网后操作", icon: "none" });
          throw e;
        }
        logError("装备更新失败", { trace_id: traceId, gear_id: id, error: err?.message }, undefined, "gear_update_failed", undefined, traceId);
        throw e;
      }
    },

    /** 删除：本地项纯本地删；云端项在线成功才删缓存视图 */
    async remove(id: number | string) {
      if (isGuestNow()) {
        const removed = removePendingGear(String(id));
        if (!removed) throw new Error("本地删除失败，请重试");
        this.gears = getPendingGears();
        return;
      }
      const uid = currentUserId();
      if (uid == null) throw new Error("未登录");
      if (typeof id === "string") {
        offlineGears.remove(uid, id);
        this.hydrate();
        return;
      }
      const traceId = createTraceId();
      try {
        logInfo("删除装备", { trace_id: traceId, gear_id: id }, undefined, "gear_delete", traceId);
        await deleteGear(id);
        setCloudGears(uid, getCloudGears(uid).filter((x) => x.id !== id));
        this.hydrate();
        logInfo("装备删除成功", { trace_id: traceId, gear_id: id }, undefined, "gear_deleted", traceId);
      } catch (e) {
        const err = e as ApiError;
        if (err && err.status === -1) {
          uni.showToast({ title: "网络不可用，请联网后操作", icon: "none" });
          throw e;
        }
        logError("装备删除失败", { trace_id: traceId, gear_id: id, error: err?.message }, undefined, "gear_delete_failed", undefined, traceId);
        throw e;
      }
    },
  },
});
