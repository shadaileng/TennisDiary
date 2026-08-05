import { defineStore } from "pinia";

import type { Diary } from "@/types";

interface DiaryState {
  diaries: Diary[]
  current: Diary | null
  loading: boolean
}

/**
 * 日记数据 store
 *
 * 管理日记列表与当前选中项。Phase1-7 网络层完成后，
 * 由 fetchList / create 等 action 对接 /api/diaries 接口。
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

    /** 拉取日记列表（Phase1-7 网络层接入后填充实现） */
    async fetchList() {
      // TODO(Phase1-7): GET /api/diaries
      this.diaries = [];
    },
  },
});
