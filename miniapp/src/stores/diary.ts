import { defineStore } from "pinia";

import { createDiary, deleteDiary, getDiaries, updateDiary } from "@/services/data";
import type { Diary, DiaryCreate, DiaryUpdate } from "@/types";
import { createTraceId, logError, logInfo } from "@/utils/eventLogger";

function getCurrentPage(): string {
  try {
    const pages = getCurrentPages();
    return pages[pages.length - 1]?.route || "";
  } catch {
    return "";
  }
}

interface DiaryState {
  diaries: Diary[]
  current: Diary | null
  loading: boolean
}

/**
 * 日记数据 store
 *
 * 管理日记列表与当前选中项，action 对接 /api/diaries 接口。
 */
export const useDiaryStore = defineStore("diary", {
  state: (): DiaryState => ({
    diaries: [],
    current: null,
    loading: false,
  }),

  getters: {
    /** 按日期倒序的日记列表（最新在前） */
    sortedDiaries: (state): Diary[] =>
      [...state.diaries].sort((a, b) => b.date.localeCompare(a.date)),
  },

  actions: {
    /** 设置列表 */
    setDiaries(list: Diary[]) {
      this.diaries = list;
    },

    /** 设置当前选中项 */
    setCurrent(diary: Diary | null) {
      this.current = diary;
    },

    /** 拉取日记列表（GET /api/diaries） */
    async fetchList() {
      this.loading = true;
      try {
        this.diaries = await getDiaries();
      } catch (e) {
        console.error("[diary] 拉取日记列表失败", e);
      } finally {
        this.loading = false;
      }
    },

    /** 创建日记（POST /api/diaries），成功后插入列表头部 */
    async create(body: DiaryCreate): Promise<Diary> {
      const traceId = createTraceId();
      try {
        logInfo("创建日记", { trace_id: traceId, type: body.type }, "diary_create");
        const d = await createDiary(body);
        this.diaries = [d, ...this.diaries];
        logInfo("日记创建成功", { trace_id: traceId, diary_id: d.id }, "diary_created");
        return d;
      } catch (e) {
        logError("日记创建失败", { trace_id: traceId, error: (e as Error).message }, "diary_create_failed");
        throw e;
      }
    },

    /** 编辑日记（PUT /api/diaries/{id}），成功后替换列表项 */
    async update(id: number, body: DiaryUpdate): Promise<Diary> {
      const traceId = createTraceId();
      try {
        logInfo("编辑日记", { trace_id: traceId, diary_id: id }, "diary_update");
        const d = await updateDiary(id, body);
        this.diaries = this.diaries.map((x) => (x.id === id ? d : x));
        logInfo("日记更新成功", { trace_id: traceId, diary_id: id }, "diary_updated");
        return d;
      } catch (e) {
        logError("日记更新失败", { trace_id: traceId, diary_id: id, error: (e as Error).message }, "diary_update_failed");
        throw e;
      }
    },

    /** 删除日记（DELETE /api/diaries/{id}），成功后从列表移除 */
    async remove(id: number) {
      const traceId = createTraceId();
      try {
        logInfo("删除日记", { trace_id: traceId, diary_id: id }, "diary_delete");
        await deleteDiary(id);
        this.diaries = this.diaries.filter((x) => x.id !== id);
        logInfo("日记删除成功", { trace_id: traceId, diary_id: id }, "diary_deleted");
      } catch (e) {
        logError("日记删除失败", { trace_id: traceId, diary_id: id, error: (e as Error).message }, "diary_delete_failed");
        throw e;
      }
    },
  },
});
