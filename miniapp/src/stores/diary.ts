import { defineStore } from "pinia";

import { createDiary, deleteDiary, getDiaries, updateDiary } from "@/services/data";
import {
  getPendingDiaries,
  upsertPendingDiary,
  updatePendingDiary,
  removePendingDiary,
  genLocalId,
} from "@/services/pendingRepo";
import { offlineDiaries } from "@/services/offlineRepo";
import { getCloudDiaries, setCloudDiaries } from "@/services/cloudCache";
import { syncOfflineData } from "@/services/sync";
import type { ApiError } from "@/services/request";
import { useAuthStore } from "@/stores/auth";
import { networkOnline } from "@/utils/network";
import type { AnyDiary, Diary, DiaryCreate, DiaryUpdate, LocalDiary } from "@/types";
import { createTraceId, logError, logInfo } from "@/utils/eventLogger";

function getCurrentPage(): string {
  try {
    const pages = getCurrentPages();
    return pages[pages.length - 1]?.route || "";
  } catch {
    return "";
  }
}

/** 类型守卫：云端日记（有数字 id） */
function isCloudDiary(x: AnyDiary): x is Diary {
  return typeof (x as Diary).id === "number";
}

/** 当前是否为游客态（action 内惰性取 auth，避免循环 import） */
function isGuestNow(): boolean {
  return useAuthStore().isGuest;
}

/** 当前登录用户 id（游客/未登录返回 null） */
function currentUserId(): number | null {
  return useAuthStore().user?.id ?? null;
}

/** 构造游客/离线本地日记实体 */
function buildLocalDiary(body: DiaryCreate, now: number): LocalDiary {
  return {
    localId: genLocalId("d"),
    pending: true,
    backendId: null,
    date: body.date,
    time: body.time || "",
    type: body.type || "训练",
    duration: body.duration || 0,
    intensity: body.intensity ?? 3,
    mood: body.mood ?? 3,
    costs: body.costs || [],
    gears: body.gears || [],
    notes: body.notes || "",
    createdAt: now,
    business_time: now,
  };
}

interface DiaryState {
  diaries: AnyDiary[]
  current: Diary | null
  loading: boolean
  /** 远端加载失败（网络层 status=-1）后置位：页面据此展示离线横幅 */
  offline: boolean
  /** 当前列表数据来自本地缓存（未命中云端） */
  fromCache: boolean
}

/**
 * 日记数据 store（Step 141 缓存合并视图）
 *
 * 渲染源恒等于 `merge(账号云端快照缓存, 账号离线新建待同步)`：
 * - 游客态：读 td_pending_*（行为零改动）
 * - 登录态：hydrate 从 cloudCache + offlineRepo 合并视图重建 state；fetchList 仅刷新缓存；
 *   离线新建落 offlineRepo；云端条目在线操作成功才改缓存视图，离线时提示。
 */
export const useDiaryStore = defineStore("diary", {
  state: (): DiaryState => ({
    diaries: [],
    current: null,
    loading: false,
    offline: false,
    fromCache: false,
  }),

  getters: {
    /** 按日期倒序的日记列表（最新在前） */
    sortedDiaries: (state): AnyDiary[] =>
      [...state.diaries].sort((a, b) => b.date.localeCompare(a.date)),
    /** 是否处于离线（缓存）渲染态 */
    isOffline: (state): boolean => state.offline,
  },

  actions: {
    /** 从缓存合并视图重建内存态（页面 onShow 先调用 → 立即渲染） */
    hydrate() {
      if (isGuestNow()) {
        this.diaries = getPendingDiaries();
        this.offline = false;
        this.fromCache = false;
        return;
      }
      const uid = currentUserId();
      if (uid == null) {
        this.diaries = [];
        return;
      }
      const cloud = getCloudDiaries(uid);
      const offline = offlineDiaries.get(uid);
      this.diaries = [...cloud, ...offline];
      this.fromCache = true;
    },

    setDiaries(list: AnyDiary[]) {
      this.diaries = list;
    },

    setCurrent(diary: Diary | null) {
      this.current = diary;
    },

    /** 取单条本地待同步日记（游客 / 登录态离线项编辑回填） */
    getLocalDiary(localId: string): LocalDiary | undefined {
      if (isGuestNow()) {
        return getPendingDiaries().find((d) => d.localId === localId);
      }
      const uid = currentUserId();
      if (uid != null) {
        const off = offlineDiaries.get(uid).find((d) => d.localId === localId);
        if (off) return off;
      }
      return getPendingDiaries().find((d) => d.localId === localId);
    },

    /** 拉取日记列表：登录态仅在「网络可用」时 GET 刷新缓存；失败（status=-1）保持缓存视图并置离线标志 */
    async fetchList() {
      if (isGuestNow()) {
        this.diaries = getPendingDiaries();
        return;
      }
      const uid = currentUserId();
      if (uid == null) return;
      // 先确保缓存视图已渲染（页面 onShow 已 hydrate；此处兜底）
      this.hydrate();
      if (!networkOnline.value) {
        this.offline = true;
        this.fromCache = true;
        return;
      }
      this.loading = true;
      try {
        const list = await getDiaries();
        setCloudDiaries(uid, list);
        // 顺带自动同步本账号离线新建
        await syncOfflineData();
        this.hydrate();
        this.offline = false;
        this.fromCache = false;
      } catch (e) {
        const err = e as ApiError;
        if (err && err.status === -1) {
          // 网络层失败：保持缓存视图，标记离线，不抛错、不清空
          this.offline = true;
          this.fromCache = true;
        } else {
          // 业务错误（含 401 由网络层处理）不降级，上抛由页面提示
          this.offline = false;
          throw e;
        }
      } finally {
        this.loading = false;
      }
    },

    /** 离线新建：写入 offlineRepo 并刷新合并视图 */
    createOffline(body: DiaryCreate): LocalDiary {
      const uid = currentUserId()!;
      const now = Math.floor(Date.now() / 1000);
      const item = buildLocalDiary(body, now);
      offlineDiaries.upsert(uid, item);
      this.hydrate();
      logInfo("离线新建日记（待同步）", { local_id: item.localId, date: body.date }, undefined, "offline_create_pending", createTraceId());
      return item;
    },

    /** 创建日记：在线成功 → 写缓存；离线/网络失败 → 落 offlineRepo */
    async create(body: DiaryCreate): Promise<AnyDiary> {
      if (isGuestNow()) {
        const now = Math.floor(Date.now() / 1000);
        const item = buildLocalDiary(body, now);
        upsertPendingDiary(item);
        this.diaries = getPendingDiaries();
        return item;
      }
      const uid = currentUserId();
      if (uid == null) throw new Error("未登录");
      if (!networkOnline.value) {
        return this.createOffline(body);
      }
      const traceId = createTraceId();
      try {
        logInfo("创建日记", { trace_id: traceId, type: body.type, date: body.date }, undefined, "diary_create", traceId);
        const d = await createDiary(body);
        setCloudDiaries(uid, [d, ...getCloudDiaries(uid)]);
        this.hydrate();
        logInfo("日记创建成功", { trace_id: traceId, diary_id: d.id }, undefined, "diary_created", traceId);
        return d;
      } catch (e) {
        const err = e as ApiError;
        if (err && err.status === -1) {
          return this.createOffline(body);
        }
        logError("日记创建失败", { trace_id: traceId, error: err?.message, type: body.type, date: body.date }, undefined, "diary_create_failed", undefined, traceId);
        throw e;
      }
    },

    /** 编辑：本地项（localId）纯本地改；云端项在线成功才改缓存视图，离线提示 */
    async update(id: number | string, body: DiaryUpdate): Promise<AnyDiary> {
      if (isGuestNow()) {
        updatePendingDiary(String(id), body as Partial<LocalDiary>);
        this.diaries = getPendingDiaries();
        return this.diaries.find((x) => (x as LocalDiary).localId === String(id))!;
      }
      const uid = currentUserId();
      if (uid == null) throw new Error("未登录");
      // 本地待同步项：纯本地更新
      if (typeof id === "string") {
        offlineDiaries.update(uid, id, body as Partial<LocalDiary>);
        this.hydrate();
        return this.diaries.find((x) => (x as LocalDiary).localId === String(id))!;
      }
      const traceId = createTraceId();
      try {
        logInfo("编辑日记", { trace_id: traceId, diary_id: id }, undefined, "diary_update", traceId);
        const d = await updateDiary(id, body);
        setCloudDiaries(uid, getCloudDiaries(uid).map((x) => (x.id === id ? d : x)));
        this.hydrate();
        logInfo("日记更新成功", { trace_id: traceId, diary_id: id }, undefined, "diary_updated", traceId);
        return d;
      } catch (e) {
        const err = e as ApiError;
        if (err && err.status === -1) {
          uni.showToast({ title: "网络不可用，请联网后操作", icon: "none" });
          throw e;
        }
        logError("日记更新失败", { trace_id: traceId, diary_id: id, error: err?.message }, undefined, "diary_update_failed", undefined, traceId);
        throw e;
      }
    },

    /** 删除：本地项纯本地删；云端项在线成功才删缓存视图，离线提示 */
    async remove(id: number | string) {
      if (isGuestNow()) {
        removePendingDiary(String(id));
        this.diaries = getPendingDiaries();
        return;
      }
      const uid = currentUserId();
      if (uid == null) throw new Error("未登录");
      if (typeof id === "string") {
        offlineDiaries.remove(uid, id);
        this.hydrate();
        return;
      }
      const traceId = createTraceId();
      try {
        logInfo("删除日记", { trace_id: traceId, diary_id: id }, undefined, "diary_delete", traceId);
        await deleteDiary(id);
        setCloudDiaries(uid, getCloudDiaries(uid).filter((x) => x.id !== id));
        this.hydrate();
        logInfo("日记删除成功", { trace_id: traceId, diary_id: id }, undefined, "diary_deleted", traceId);
      } catch (e) {
        const err = e as ApiError;
        if (err && err.status === -1) {
          uni.showToast({ title: "网络不可用，请联网后操作", icon: "none" });
          throw e;
        }
        logError("日记删除失败", { trace_id: traceId, diary_id: id, error: err?.message }, undefined, "diary_delete_failed", undefined, traceId);
        throw e;
      }
    },
  },
});
