/**
 * 通用本地存储基座（Step 141）
 *
 * 自 pendingRepo（Step 129）下沉的底层能力，供游客仓库（pendingRepo）、
 * 登录态离线仓库（offlineRepo）、账号云端快照缓存（cloudCache）共同复用。
 *
 * 能力：
 * - `genLocalId(prefix)`：生成本地唯一 id
 * - `estimateSize(value)` / `CAPACITY_LIMIT`：单 key 容量保护（~900KB）
 * - `persist(key, value)`：写回 storage，容量/异常容错（不抛错，返回 false）
 * - `load<T>(key)`：读数组（损坏容错 → 返回 [] 并清理坏键）
 * - `loadRaw<T>(key)`：读任意对象（损坏容错 → 返回 null 并清理坏键）
 *
 * 本模块不依赖任何 store / request，仅用 uni.* 与常量，避免循环依赖。
 */

/** 单 key 容量安全阈值（wx storage 单 key 上限 1MB，留安全余量） */
export const CAPACITY_LIMIT = 900 * 1024;

/** 生成本地唯一 id：`{prefix}_{时间戳}_{随机串}`，避免 tab 快速操作撞 key */
export function genLocalId(prefix: string): string {
  const rand = Math.random().toString(36).slice(2, 8);
  return `${prefix}_${Date.now()}_${rand}`;
}

/** 估算 JSON 序列化长度（字节） */
export function estimateSize(value: unknown): number {
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
export function persist(key: string, value: unknown, opts?: { silent?: boolean }): boolean {
  if (estimateSize(value) > CAPACITY_LIMIT) {
    if (!opts?.silent) {
      uni.showToast({ title: "本地空间不足，请先登录同步", icon: "none" });
    }
    return false;
  }
  try {
    uni.setStorageSync(key, JSON.stringify(value));
    return true;
  } catch {
    if (!opts?.silent) {
      uni.showToast({ title: "本地保存失败，请先登录同步", icon: "none" });
    }
    return false;
  }
}

/** 读数组（损坏容错：parse 失败 → 返回 [] 并清理坏键） */
export function load<T>(key: string): T[] {
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

/** 读任意对象（损坏容错：parse 失败 → 返回 null 并清理坏键） */
export function loadRaw<T>(key: string): T | null {
  try {
    const raw = uni.getStorageSync(key) as string;
    if (!raw) return null;
    return JSON.parse(raw) as T;
  } catch {
    uni.removeStorageSync(key);
    return null;
  }
}
