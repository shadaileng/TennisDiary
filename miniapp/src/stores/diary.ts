import { defineStore } from "pinia";

import { createDiary, deleteDiary, getDiaries, updateDiary } from "@/services/data";
import {
  getPendingDiaries,
  upsertPendingDiary,
  updatePendingDiary,
  removePendingDiary,
  genLocalId,
} from "@/services/pendingRepo";
import { useAuthStore } from "@/stores/auth";
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

interface DiaryState {
  diaries: AnyDiary[]
  current: Diary | null
  loading: boolean
}

/**
 * 日记数据 store（Step 129 双路径）
 *
 * 登录态逻辑与现状一致（对接 /api/diaries）；游客态读写本地待同步仓库（pendingRepo），
 * 页面按 `getEntryId`/`isLocalEntry` 消费云端与本地联合实体。
 */
export const useDiaryStore = defineStore("diary", {
  state: (): DiaryState => ({
    diaries: [],
    current: null,
    loading: false,
  }),

  getters: {
    /** 按日期倒序的日记列表（最新在前） */
    sortedDiaries: (state): AnyDiary[] =>
      [...state.diaries].sort((a, b) => b.date.localeCompare(a.date)),
  },

  actions: {
    /** 设置列表 */
    setDiaries(list: AnyDiary[]) {
      this.diaries = list;
    },

    /** 设置当前选中项 */
    setCurrent(diary: Diary | null) {
      this.current = diary;
    },

    /** 取单条本地待同步日记（游客态编辑回填） */
    getLocalDiary(localId: string): LocalDiary | undefined {
      return getPendingDiaries().find((d) => d.localId === localId);
    },

    /** 拉取日记列表（GET /api/diaries）；游客态从本地仓库载入 */
    async fetchList() {
      if (isGuestNow()) {
        this.diaries = getPendingDiaries();
        return;
      }
      this.loading = true;
      try {
        this.diaries = await getDiaries();
      } catch (e) {
        logError("日记列表加载失败", { error: (e as Error).message }, undefined, "diary_list_load_failed", undefined, createTraceId());
      } finally {
        this.loading = false;
      }
    },

    /** 创建日记：登录态 POST；游客态写入本地仓库 */
    async create(body: DiaryCreate): Promise<AnyDiary> {
      if (isGuestNow()) {
        const now = Math.floor(Date.now() / 1000);
        const item: LocalDiary = {
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
        upsertPendingDiary(item);
        this.diaries = getPendingDiaries();
        return item;
      }
      const traceId = createTraceId();
      try {
        logInfo("创建日记", { trace_id: traceId, type: body.type, date: body.date, time: body.time, duration: body.duration, intensity: body.intensity, mood: body.mood, costs: body.costs, gears: body.gears, notes: body.notes }, undefined, "diary_create", traceId);
        const d = await createDiary(body);
        this.diaries = [d, ...this.diaries];
        logInfo("日记创建成功", { trace_id: traceId, diary_id: d.id, type: d.type, duration: d.duration }, undefined, "diary_created", traceId);
        return d;
      } catch (e) {
        logError("日记创建失败", { trace_id: traceId, error: (e as Error).message, type: body.type, date: body.date, duration: body.duration }, undefined, "diary_create_failed", undefined, traceId);
        throw e;
      }
    },

    /** 编辑日记：登录态 PUT；游客态按 localId 更新本地项 */
    async update(id: number | string, body: DiaryUpdate): Promise<AnyDiary> {
      if (isGuestNow()) {
        updatePendingDiary(String(id), body as Partial<LocalDiary>);
        this.diaries = getPendingDiaries();
        return this.diaries.find((x) => (x as LocalDiary).localId === String(id))!;
      }
      const traceId = createTraceId();
      try {
        logInfo("编辑日记", { trace_id: traceId, diary_id: id, type: body.type, date: body.date, time: body.time, duration: body.duration, intensity: body.intensity, mood: body.mood, costs: body.costs, gears: body.gears, notes: body.notes }, undefined, "diary_update", traceId);
        const d = await updateDiary(id as number, body);
        this.diaries = this.diaries.map((x) => (isCloudDiary(x) && x.id === id ? d : x));
        logInfo("日记更新成功", { trace_id: traceId, diary_id: id, type: d.type, duration: d.duration }, undefined, "diary_updated", traceId);
        return d;
      } catch (e) {
        logError("日记更新失败", { trace_id: traceId, diary_id: id, error: (e as Error).message, type: body.type, date: body.date, duration: body.duration }, undefined, "diary_update_failed", undefined, traceId);
        throw e;
      }
    },

    /** 删除日记：登录态 DELETE；游客态按 localId 删除本地项 */
    async remove(id: number | string) {
      if (isGuestNow()) {
        removePendingDiary(String(id));
        this.diaries = getPendingDiaries();
        return;
      }
      const traceId = createTraceId();
      try {
        logInfo("删除日记", { trace_id: traceId, diary_id: id }, undefined, "diary_delete", traceId);
        await deleteDiary(id as number);
        this.diaries = this.diaries.filter((x) => !(isCloudDiary(x) && x.id === id));
        logInfo("日记删除成功", { trace_id: traceId, diary_id: id }, undefined, "diary_deleted", traceId);
      } catch (e) {
        logError("日记删除失败", { trace_id: traceId, diary_id: id, error: (e as Error).message }, undefined, "diary_delete_failed", undefined, traceId);
        throw e;
      }
    },
  },
});
