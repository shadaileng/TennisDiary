/**
 * 游客本地数据 → 云端同步服务（Step 129 登录后自动静默同步）
 *
 * 登录成功后由 mine.vue 触发：把本地待同步的体重/日记/装备逐条 POST 到后台，
 * 单条成功即从本地仓库移除；失败保留该条并计数，下次登录自动重试。
 *
 * - 顺序固定：先体重（无大字段、快）→ 再日记 → 最后装备（含 dataURL 封面，最重）
 * - 串行 await，避免并发请求轰炸后台
 * - 进程级防并发：模块级 syncing 布尔 + 每次取 pending 快照，避免与页面并发写冲突
 * - 装备封面 dataURL 需先写为临时文件 → 走正式受检 /upload/gear-image → URL 后再 createGear
 * - 不打印 photo/dataURL 等大字段（只打 ok/fail 计数与类型）
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
import { useAuthStore } from "@/stores/auth";
import type { DiaryCreate, GearCreate, WeightCreate } from "@/types";
import { createTraceId, logInfo } from "@/utils/eventLogger";
import { uploadGearImage } from "@/utils/index";

/** 进程级防并发标记 */
let syncing = false;

export interface SyncResult {
  diariesOk: number
  diariesFail: number
  gearsOk: number
  gearsFail: number
  weightsOk: number
  weightsFail: number
}

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

async function syncWeights(): Promise<{ ok: number; fail: number }> {
  const list = getPendingWeights();
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
  const list = getPendingDiaries();
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
  const list = getPendingGears();
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
 * 登录成功后静默同步全部本地待同步数据。仅登录态执行，进程级防并发。
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
