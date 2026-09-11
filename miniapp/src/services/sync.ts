/**
 * 本地数据 → 云端同步服务
 *
 * 两部分，互不干扰、各自独立锁：
 * - `syncPendingLocalData`（Step 129）：游客本地仓库（td_pending_*）→ 云端，登录成功后触发。
 * - `syncOfflineData`（Step 141）：登录态离线仓库（td_offline_{userId}_*）→ 云端，
 *   网络恢复 / 登录成功 / 下拉刷新在线成功后自动触发；按 business_time 升序串行补传，
 *   成功后写入账号云端快照缓存并移除离线项，再刷新相关 store 视图。
 *
 * 装备封面 dataURL 需先写为临时文件 → 走正式受检 /upload/gear-image → URL 后再 createGear。
 * 不打印 photo/dataURL 等大字段（只打 ok/fail 计数与类型）。
 */

import { createGear, createDiary, createWeight } from "@/services/data";
import {
  getPendingDiaries,
  getPendingGears,
  getPendingWeights,
  removePendingDiary,
  removePendingGear,
  removePendingWeight,
} from "@/services/pendingRepo";
import {
  offlineDiaries,
  offlineGears,
  offlineWeights,
} from "@/services/offlineRepo";
import {
  getCloudDiaries,
  getCloudGears,
  getCloudWeights,
  setCloudDiaries,
  setCloudGears,
  setCloudWeights,
} from "@/services/cloudCache";
import { useAuthStore } from "@/stores/auth";
import type { DiaryCreate, GearCreate, WeightCreate } from "@/types";
import { createTraceId, logError, logInfo } from "@/utils/eventLogger";
import { uploadGearImage } from "@/utils/index";

/** 进程级防并发标记（游客同步） */
let syncing = false;
/** 进程级防并发标记（登录态离线同步） */
let syncingOffline = false;

export interface SyncResult {
  diariesOk: number
  diariesFail: number
  gearsOk: number
  gearsFail: number
  weightsOk: number
  weightsFail: number
}

export interface SyncOfflineResult {
  diariesOk: number
  diariesFail: number
  gearsOk: number
  gearsFail: number
  weightsOk: number
  weightsFail: number
}

const EMPTY_OFFLINE: SyncOfflineResult = {
  diariesOk: 0, diariesFail: 0, gearsOk: 0, gearsFail: 0, weightsOk: 0, weightsFail: 0,
};

/** 将 dataURL（`data:image/png;base64,...`）写为临时文件路径，供 uploadFile 使用 */
function dataUrlToTempFile(dataUrl: string): Promise<string> {
  return new Promise((resolve, reject) => {
    const m = /^data:([^;]+);base64,(.+)$/s.exec(dataUrl);
    if (!m) return reject(new Error("封面数据格式无效"));
    const extMap: Record<string, string> = {
      "image/jpeg": ".jpg",
      "image/png": ".png",
      "image/webp": ".webp",
    };
    const ext = extMap[m[1].toLowerCase()] || ".png";
    const filePath = `${wx.env.USER_DATA_PATH}/td_sync_gear_${Date.now()}_${Math.random().toString(36).slice(2, 8)}${ext}`;
    try {
      const fs = uni.getFileSystemManager();
      fs.writeFile({
        filePath,
        data: m[2],
        encoding: "base64",
        success: () => resolve(filePath),
        fail: (err) => reject(new Error(err.errMsg || "封面临时文件写入失败")),
      });
    } catch (e) {
      reject(e as Error);
    }
  });
}

// ===================== 游客本地同步（Step 129，零改动） =====================

async function syncWeights(): Promise<{ ok: number; fail: number }> {
  const list = [...getPendingWeights()].sort((a, b) => a.createdAt - b.createdAt);
  let ok = 0;
  let fail = 0;
  for (const w of list) {
    try {
      await createWeight({
        date: w.date,
        weight: w.weight,
        bust: w.bust,
        waist: w.waist,
        hip: w.hip,
        business_time: w.business_time,
      } as WeightCreate);
      removePendingWeight(w.localId);
      ok++;
    } catch {
      fail++;
    }
  }
  return { ok, fail };
}

async function syncDiaries(): Promise<{ ok: number; fail: number }> {
  const list = [...getPendingDiaries()].sort((a, b) => a.createdAt - b.createdAt);
  let ok = 0;
  let fail = 0;
  for (const d of list) {
    try {
      await createDiary({
        date: d.date,
        time: d.time,
        type: d.type,
        duration: d.duration,
        intensity: d.intensity,
        mood: d.mood,
        costs: d.costs,
        gears: d.gears,
        notes: d.notes,
        business_time: d.business_time,
      } as DiaryCreate);
      removePendingDiary(d.localId);
      ok++;
    } catch {
      fail++;
    }
  }
  return { ok, fail };
}

async function syncGears(): Promise<{ ok: number; fail: number }> {
  const list = [...getPendingGears()].sort((a, b) => a.createdAt - b.createdAt);
  let ok = 0;
  let fail = 0;
  for (const g of list) {
    try {
      let photo: string | undefined;
      if (g.photo && g.photo.startsWith("data:")) {
        // 本地 dataURL 封面 → 写临时文件 → 正式受检上传换服务器 URL
        const tempPath = await dataUrlToTempFile(g.photo);
        photo = await uploadGearImage(tempPath);
      } else if (g.photo) {
        photo = g.photo;
      }
      await createGear({
        category: g.category,
        name: g.name,
        buy_date: g.buy_date,
        price: g.price,
        feeling: g.feeling,
        photo,
        business_time: g.business_time,
      } as GearCreate);
      removePendingGear(g.localId);
      ok++;
    } catch {
      fail++;
    }
  }
  return { ok, fail };
}

/**
 * 登录成功后静默同步全部游客本地待同步数据。仅登录态执行，进程级防并发。
 * 单条失败不中断批量；不主动 toast 打扰（可由调用方按 fail 提示）。
 */
export async function syncPendingLocalData(): Promise<SyncResult> {
  const auth = useAuthStore();
  const empty: SyncResult = { diariesOk: 0, diariesFail: 0, gearsOk: 0, gearsFail: 0, weightsOk: 0, weightsFail: 0 };
  if (!auth.isLoggedIn || syncing) return empty;
  syncing = true;
  const traceId = createTraceId();
  try {
    const weights = await syncWeights();
    const diaries = await syncDiaries();
    const gears = await syncGears();
    const result: SyncResult = {
      diariesOk: diaries.ok,
      diariesFail: diaries.fail,
      gearsOk: gears.ok,
      gearsFail: gears.fail,
      weightsOk: weights.ok,
      weightsFail: weights.fail,
    };
    logInfo(
      "本地数据同步完成",
      { trace_id: traceId, ...result },
      undefined,
      "pending_sync_done",
      traceId,
    );
    return result;
  } finally {
    syncing = false;
  }
}

// ===================== 登录态离线同步（Step 141） =====================

async function syncOfflineWeights(uid: number): Promise<{ ok: number; fail: number }> {
  const list = [...offlineWeights.get(uid)].sort((a, b) => a.business_time - b.business_time);
  let ok = 0;
  let fail = 0;
  for (const w of list) {
    try {
      const rec = await createWeight({
        date: w.date,
        weight: w.weight,
        bust: w.bust,
        waist: w.waist,
        hip: w.hip,
        business_time: w.business_time,
      } as WeightCreate);
      setCloudWeights(uid, [rec, ...getCloudWeights(uid)]);
      offlineWeights.remove(uid, w.localId);
      ok++;
    } catch {
      fail++;
    }
  }
  return { ok, fail };
}

async function syncOfflineDiaries(uid: number): Promise<{ ok: number; fail: number }> {
  const list = [...offlineDiaries.get(uid)].sort((a, b) => a.business_time - b.business_time);
  let ok = 0;
  let fail = 0;
  for (const d of list) {
    try {
      const rec = await createDiary({
        date: d.date,
        time: d.time,
        type: d.type,
        duration: d.duration,
        intensity: d.intensity,
        mood: d.mood,
        costs: d.costs,
        gears: d.gears,
        notes: d.notes,
        business_time: d.business_time,
      } as DiaryCreate);
      setCloudDiaries(uid, [rec, ...getCloudDiaries(uid)]);
      offlineDiaries.remove(uid, d.localId);
      ok++;
    } catch {
      fail++;
    }
  }
  return { ok, fail };
}

async function syncOfflineGears(uid: number): Promise<{ ok: number; fail: number }> {
  const list = [...offlineGears.get(uid)].sort((a, b) => a.business_time - b.business_time);
  let ok = 0;
  let fail = 0;
  for (const g of list) {
    try {
      let photo: string | undefined;
      if (g.photo && g.photo.startsWith("data:")) {
        const tempPath = await dataUrlToTempFile(g.photo);
        photo = await uploadGearImage(tempPath);
      } else if (g.photo) {
        photo = g.photo;
      }
      const rec = await createGear({
        category: g.category,
        name: g.name,
        buy_date: g.buy_date,
        price: g.price,
        feeling: g.feeling,
        photo,
        business_time: g.business_time,
      } as GearCreate);
      setCloudGears(uid, [rec, ...getCloudGears(uid)]);
      offlineGears.remove(uid, g.localId);
      ok++;
    } catch {
      fail++;
    }
  }
  return { ok, fail };
}

/** 同步后刷新相关 store 视图（动态 import 避免与 store 循环依赖） */
async function refreshStores(): Promise<void> {
  const [{ useDiaryStore }, { useGearStore }, { useWeightStore }] = await Promise.all([
    import("@/stores/diary"),
    import("@/stores/gear"),
    import("@/stores/weight"),
  ]);
  useDiaryStore().hydrate();
  useGearStore().hydrate();
  useWeightStore().hydrate();
}

/**
 * 登录态离线新建自动同步：仅在已登录且未并发时执行，按 business_time 升序串行补传。
 * 单条失败保留并计数；成功后写账号云端快照缓存、移除离线项、刷新视图。
 * 轻提示与埋点交由调用方/网络恢复场景决定，本函数仅记日志。
 */
export async function syncOfflineData(): Promise<SyncOfflineResult> {
  const auth = useAuthStore();
  if (!auth.isLoggedIn || syncingOffline) return EMPTY_OFFLINE;
  const uid = auth.user?.id;
  if (uid == null) return EMPTY_OFFLINE;
  syncingOffline = true;
  const traceId = createTraceId();
  try {
    const weights = await syncOfflineWeights(uid);
    const diaries = await syncOfflineDiaries(uid);
    const gears = await syncOfflineGears(uid);
    const result: SyncOfflineResult = {
      diariesOk: diaries.ok,
      diariesFail: diaries.fail,
      gearsOk: gears.ok,
      gearsFail: gears.fail,
      weightsOk: weights.ok,
      weightsFail: weights.fail,
    };
    const total = result.diariesOk + result.diariesFail + result.gearsOk + result.gearsFail + result.weightsOk + result.weightsFail;
    if (total > 0) {
      logInfo("离线待同步数据同步完成", { trace_id: traceId, ...result }, undefined, "offline_sync_done", traceId);
    }
    if (total > 0) await refreshStores();
    return result;
  } catch (e) {
    logError("离线同步异常", { trace_id: traceId, error: (e as Error).message }, undefined, "offline_sync_failed", undefined, traceId);
    return EMPTY_OFFLINE;
  } finally {
    syncingOffline = false;
  }
}
