import { defineStore } from "pinia";

import { createWeight, deleteWeight, getWeights } from "@/services/data";
import {
  getPendingWeights,
  upsertPendingWeight,
  removePendingWeight,
  genLocalId,
} from "@/services/pendingRepo";
import { offlineWeights } from "@/services/offlineRepo";
import { getCloudWeights, setCloudWeights } from "@/services/cloudCache";
import { syncOfflineData } from "@/services/sync";
import type { ApiError } from "@/services/request";
import { useAuthStore } from "@/stores/auth";
import { networkOnline } from "@/utils/network";
import type { AnyWeight, LocalWeight, WeightCreate, WeightRecord } from "@/types";
import { createTraceId, logError, logInfo } from "@/utils/eventLogger";
import { EV } from "@/utils/eventConstants";

function getCurrentPage(): string {
  try {
    const pages = getCurrentPages();
    return pages[pages.length - 1]?.route || "";
  } catch {
    return "";
  }
}

function isCloudWeight(x: AnyWeight): x is WeightRecord {
  return typeof (x as WeightRecord).id === "number";
}

function isGuestNow(): boolean {
  return useAuthStore().isGuest;
}

function currentUserId(): number | null {
  return useAuthStore().user?.id ?? null;
}

/** 构造游客/离线本地体重实体 */
function buildLocalWeight(body: WeightCreate, now: number): LocalWeight {
  return {
    localId: genLocalId("w"),
    pending: true,
    backendId: null,
    date: body.date,
    weight: body.weight,
    bust: body.bust,
    waist: body.waist,
    hip: body.hip,
    createdAt: now,
    business_time: now,
  };
}

interface WeightState {
  weights: AnyWeight[]
  loading: boolean
  offline: boolean
  fromCache: boolean
}

/**
 * 体重数据 store（Step 141 缓存合并视图）
 *
 * 同 diary/gear：渲染源 = merge(cloudCache, offlineRepo)；游客态零改动。
 */
export const useWeightStore = defineStore("weight", {
  state: (): WeightState => ({
    weights: [],
    loading: false,
    offline: false,
    fromCache: false,
  }),

  getters: {
    /** 按日期倒序的体重记录（最新在前） */
    sortedWeights: (state): AnyWeight[] =>
      [...state.weights].sort((a, b) => b.date.localeCompare(a.date)),
    isOffline: (state): boolean => state.offline,
  },

  actions: {
    hydrate() {
      if (isGuestNow()) {
        this.weights = getPendingWeights();
        this.offline = false;
        this.fromCache = false;
        return;
      }
      const uid = currentUserId();
      if (uid == null) {
        this.weights = [];
        return;
      }
      this.weights = [...getCloudWeights(uid), ...offlineWeights.get(uid)];
      this.fromCache = true;
    },

    setWeights(list: AnyWeight[]) {
      this.weights = list;
    },

    /** 拉取体重记录：登录态仅网络可用时 GET 刷新缓存；失败保持缓存视图 */
    async fetchList() {
      if (isGuestNow()) {
        this.weights = getPendingWeights();
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
        const list = await getWeights();
        setCloudWeights(uid, list);
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
    createOffline(body: WeightCreate): LocalWeight {
      const uid = currentUserId()!;
      const now = Math.floor(Date.now() / 1000);
      const item = buildLocalWeight(body, now);
      offlineWeights.upsert(uid, item);
      this.hydrate();
      logInfo("离线新建体重（待同步）", { local_id: item.localId, date: body.date }, undefined, EV.WEIGHT_OFFLINE_CREATE_PENDING, createTraceId());
      return item;
    },

    /** 记录体重：在线成功 → 写缓存；离线/网络失败 → 落 offlineRepo */
    async create(body: WeightCreate): Promise<AnyWeight> {
      if (isGuestNow()) {
        const now = Math.floor(Date.now() / 1000);
        const item = buildLocalWeight(body, now);
        upsertPendingWeight(item);
        this.weights = getPendingWeights();
        return item;
      }
      const uid = currentUserId();
      if (uid == null) throw new Error("未登录");
      if (!networkOnline.value) {
        return this.createOffline(body);
      }
      const traceId = createTraceId();
      try {
        logInfo("记录体重", { date: body.date, weight: body.weight }, undefined, EV.WEIGHT_CREATE, traceId);
        const w = await createWeight(body);
        setCloudWeights(uid, [w, ...getCloudWeights(uid)]);
        this.hydrate();
        logInfo("体重记录成功", { weight_id: w.id }, undefined, EV.WEIGHT_CREATED, traceId);
        return w;
      } catch (e) {
        const err = e as ApiError;
        if (err && err.status === -1) {
          return this.createOffline(body);
        }
        logError("体重记录失败", { error: err?.message, date: body.date }, undefined, EV.WEIGHT_CREATE_FAILED, undefined, traceId);
        throw e;
      }
    },

    /** 删除：本地项纯本地删；云端项在线成功才删缓存视图 */
    async remove(id: number | string) {
      if (isGuestNow()) {
        removePendingWeight(String(id));
        this.weights = getPendingWeights();
        return;
      }
      const uid = currentUserId();
      if (uid == null) throw new Error("未登录");
      if (typeof id === "string") {
        offlineWeights.remove(uid, id);
        this.hydrate();
        return;
      }
      const traceId = createTraceId();
      try {
        logInfo("删除体重记录", { weight_id: id }, undefined, EV.WEIGHT_DELETE, traceId);
        await deleteWeight(id);
        setCloudWeights(uid, getCloudWeights(uid).filter((x) => x.id !== id));
        this.hydrate();
        logInfo("体重记录删除成功", { weight_id: id }, undefined, EV.WEIGHT_DELETED, traceId);
      } catch (e) {
        const err = e as ApiError;
        if (err && err.status === -1) {
          uni.showToast({ title: "网络不可用，请联网后操作", icon: "none" });
          throw e;
        }
        logError("体重记录删除失败", { weight_id: id, error: err?.message }, undefined, EV.WEIGHT_DELETE_FAILED, undefined, traceId);
        throw e;
      }
    },
  },
});
