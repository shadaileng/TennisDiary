/**
 * 本地待同步仓库（Step 129 游客本地降级）
 *
 * 封装三实体（diary/gear/weight）在本地 storage 的读写与增删改，供游客态离线完整使用。
 * - storage 键见 `constants/storage.ts`（`td_pending_*`，沿用 `td_cost_tags` 本地持久化先例）
 * - 数据形态：每个 storage 值为 `LocalXxx[]`（见 `types/index.ts`）
 * - 容量容错：写前估算序列化长度，超过单 key 阈值时 toast 提示并返回 false，不写坏数据
 * - 损坏容错：JSON.parse 失败 → 返回 [] 并清理坏键，不崩溃
 *
 * 依赖注入：本模块不依赖任何 store / request，仅用 uni.* 与常量，避免循环依赖。
 */

import { STORAGE_KEYS } from "@/constants/storage";
import type { LocalDiary, LocalGear, LocalWeight } from "@/types";

/** 单 key 容量安全阈值（wx storage 单 key 上限 1MB，留安全余量） */
const CAPACITY_LIMIT = 900 * 1024;

/** 生成本地唯一 id：`{prefix}_{时间戳}_{随机串}`，避免 tab 快速操作撞 key */
export function genLocalId(prefix: string): string {
  const rand = Math.random().toString(36).slice(2, 8);
  return `${prefix}_${Date.now()}_${rand}`;
}

/** 估算 JSON 序列化长度（字节） */
function estimateSize(value: unknown): number {
  try {
    return JSON.stringify(value).length;
  } catch {
    return Number.MAX_SAFE_INTEGER;
  }
}

/**
 * 写回 storage。容量不足或写入异常时返回 false（调用方可选择保留内存态）。
 * 不在此抛错：存储失败不应导致页面崩溃，交由调用方决策。
 */
function persist(key: string, value: unknown): boolean {
  if (estimateSize(value) > CAPACITY_LIMIT) {
    uni.showToast({ title: "本地空间不足，请先登录同步", icon: "none" });
    return false;
  }
  try {
    uni.setStorageSync(key, JSON.stringify(value));
    return true;
  } catch {
    uni.showToast({ title: "本地保存失败，请先登录同步", icon: "none" });
    return false;
  }
}

/** 读全量（损坏容错：parse 失败 → 返回 [] 并清理坏键） */
function load<T>(key: string): T[] {
  try {
    const raw = uni.getStorageSync(key) as string;
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? (parsed as T[]) : [];
  } catch {
    uni.removeStorageSync(key);
    return [];
  }
}

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
