/**
 * 登录态离线待同步仓库（Step 141）
 *
 * 与游客仓库 pendingRepo 同构，但按 userId 账号隔离（键 `td_offline_{userId}_*`），
 * 供「已登录用户在断网时新建」的日记/装备/体重落地，恢复网络后由 syncOfflineData 自动补传。
 *
 * 实体复用 LocalDiary/LocalGear/LocalWeight（PendingMeta + business_time），
 * business_time 由调用方（store.create）在构造时填入 now()，本仓库只负责持久化。
 *
 * 零 store 依赖，避免与 store 循环引用（store 会 import 本模块）。
 */

import { genLocalId, load, persist } from "@/services/storageBase";
import { offlineKey } from "@/constants/storage";
import type { LocalDiary, LocalGear, LocalWeight } from "@/types";

type OfflineEntity = "diaries" | "gears" | "weights";

interface OfflineRepo<T extends { localId: string }> {
  get(userId: number): T[];
  save(userId: number, list: T[]): boolean;
  /** 头插（新建）；已存在 localId 则覆盖 */
  upsert(userId: number, item: T): boolean;
  /** 按 localId 局部更新（保留 localId/pending） */
  update(userId: number, localId: string, patch: Partial<T>): boolean;
  /** 按 localId 删除 */
  remove(userId: number, localId: string): boolean;
}

function makeOfflineRepo<T extends { localId: string }>(entity: OfflineEntity): OfflineRepo<T> {
  return {
    get(userId) {
      return load<T>(offlineKey(userId, entity));
    },
    save(userId, list) {
      return persist(offlineKey(userId, entity), list);
    },
    upsert(userId, item) {
      const list = load<T>(offlineKey(userId, entity));
      const idx = list.findIndex((x) => x.localId === item.localId);
      if (idx >= 0) list[idx] = item;
      else list.unshift(item);
      return persist(offlineKey(userId, entity), list);
    },
    update(userId, localId, patch) {
      const list = load<T>(offlineKey(userId, entity));
      const idx = list.findIndex((x) => x.localId === localId);
      if (idx < 0) return false;
      list[idx] = { ...list[idx], ...patch, localId } as T;
      return persist(offlineKey(userId, entity), list);
    },
    remove(userId, localId) {
      const list = load<T>(offlineKey(userId, entity));
      const next = list.filter((x) => x.localId !== localId);
      if (next.length === list.length) return false;
      return persist(offlineKey(userId, entity), next);
    },
  };
}

export const offlineDiaries = makeOfflineRepo<LocalDiary>("diaries");
export const offlineGears = makeOfflineRepo<LocalGear>("gears");
export const offlineWeights = makeOfflineRepo<LocalWeight>("weights");

/** 重新导出，方便调用方统一从本模块取本地 id 生成器 */
export { genLocalId };
