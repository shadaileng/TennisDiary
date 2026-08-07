import { defineStore } from "pinia";

import { createDiary, deleteDiary, getDiaries, updateDiary } from "@/services/data";
import type { Diary, DiaryCreate, DiaryUpdate } from "@/types";

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
      const d = await createDiary(body);
      this.diaries = [d, ...this.diaries];
      return d;
    },

    /** 编辑日记（PUT /api/diaries/{id}），成功后替换列表项 */
    async update(id: number, body: DiaryUpdate): Promise<Diary> {
      const d = await updateDiary(id, body);
      this.diaries = this.diaries.map((x) => (x.id === id ? d : x));
      if (this.current?.id === id) {
        this.current = d;
      }
      return d;
    },

    /** 删除日记（DELETE /api/diaries/{id}），成功后从列表移除 */
    async remove(id: number) {
      await deleteDiary(id);
      this.diaries = this.diaries.filter((x) => x.id !== id);
      if (this.current?.id === id) {
        this.current = null;
      }
    },
  },
});
