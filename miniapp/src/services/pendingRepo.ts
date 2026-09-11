/**
 * 游客本地待同步仓库（Step 129 游客本地降级）
 *
 * 封装三实体（diary/gear/weight）在本地 storage 的读写与增删改，供游客态离线完整使用。
 * - storage 键见 `constants/storage.ts`（`td_pending_*`，沿用 `td_cost_tags` 本地持久化先例）
 * - 数据形态：每个 storage 值为 `LocalXxx[]`（见 `types/index.ts`）
 * - 底层能力（load/persist/容量保护/损坏容错/genLocalId）自 Step 141 起统一复用 `storageBase`
 *
 * 依赖注入：本模块不依赖任何 store / request，仅用 uni.* 与常量，避免循环依赖。
 */

import { STORAGE_KEYS } from "@/constants/storage";
import { genLocalId, load, persist } from "@/services/storageBase";
import type { LocalDiary, LocalGear, LocalWeight } from "@/types";

// 对外 API、游客键、行为完全不变；仅底层实现下沉到 storageBase。
// 保留 genLocalId 的再导出，兼容既有从 pendingRepo 引入的调用方（stores/*）。
export { genLocalId };

// ==================== 日记 ====================

export function getPendingDiaries(): LocalDiary[] {
  return load<LocalDiary>(STORAGE_KEYS.pendingDiaries);
}

export function savePendingDiaries(list: LocalDiary[]): boolean {
  return persist(STORAGE_KEYS.pendingDiaries, list);
}

/** 头插（游客新建），返回持久化成功与否 */
export function upsertPendingDiary(item: LocalDiary): boolean {
  const list = getPendingDiaries();
  const idx = list.findIndex((x) => x.localId === item.localId);
  if (idx >= 0) {
    list[idx] = item;
  } else {
    list.unshift(item);
  }
  return savePendingDiaries(list);
}

/** 按 localId 局部更新（保留 localId/pending/backendId/createdAt），返回是否成功 */
export function updatePendingDiary(localId: string, patch: Partial<LocalDiary>): boolean {
  const list = getPendingDiaries();
  const idx = list.findIndex((x) => x.localId === localId);
  if (idx < 0) return false;
  list[idx] = { ...list[idx], ...patch, localId, pending: true };
  return savePendingDiaries(list);
}

/** 按 localId 删除（登录同步成功/用户删除时调用） */
export function removePendingDiary(localId: string): boolean {
  const list = getPendingDiaries();
  const next = list.filter((x) => x.localId !== localId);
  if (next.length === list.length) return false;
  return savePendingDiaries(next);
}

// ==================== 装备 ====================

export function getPendingGears(): LocalGear[] {
  return load<LocalGear>(STORAGE_KEYS.pendingGears);
}

export function savePendingGears(list: LocalGear[]): boolean {
  return persist(STORAGE_KEYS.pendingGears, list);
}

export function upsertPendingGear(item: LocalGear): boolean {
  const list = getPendingGears();
  const idx = list.findIndex((x) => x.localId === item.localId);
  if (idx >= 0) {
    list[idx] = item;
  } else {
    list.unshift(item);
  }
  return savePendingGears(list);
}

export function updatePendingGear(localId: string, patch: Partial<LocalGear>): boolean {
  const list = getPendingGears();
  const idx = list.findIndex((x) => x.localId === localId);
  if (idx < 0) return false;
  list[idx] = { ...list[idx], ...patch, localId, pending: true };
  return savePendingGears(list);
}

export function removePendingGear(localId: string): boolean {
  const list = getPendingGears();
  const next = list.filter((x) => x.localId !== localId);
  if (next.length === list.length) return false;
  return savePendingGears(next);
}

// ==================== 体重 ====================

export function getPendingWeights(): LocalWeight[] {
  return load<LocalWeight>(STORAGE_KEYS.pendingWeights);
}

export function savePendingWeights(list: LocalWeight[]): boolean {
  return persist(STORAGE_KEYS.pendingWeights, list);
}

export function upsertPendingWeight(item: LocalWeight): boolean {
  const list = getPendingWeights();
  const idx = list.findIndex((x) => x.localId === item.localId);
  if (idx >= 0) {
    list[idx] = item;
  } else {
    list.unshift(item);
  }
  return savePendingWeights(list);
}

export function updatePendingWeight(localId: string, patch: Partial<LocalWeight>): boolean {
  const list = getPendingWeights();
  const idx = list.findIndex((x) => x.localId === localId);
  if (idx < 0) return false;
  list[idx] = { ...list[idx], ...patch, localId, pending: true };
  return savePendingWeights(list);
}

export function removePendingWeight(localId: string): boolean {
  const list = getPendingWeights();
  const next = list.filter((x) => x.localId !== localId);
  if (next.length === list.length) return false;
  return savePendingWeights(next);
}
