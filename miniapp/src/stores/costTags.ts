import { defineStore } from "pinia";

import { STORAGE_KEYS } from "@/constants/storage";
import { DEFAULT_COST_PRESETS } from "@/utils";

/** storage 键名统一从常量读取 */
const COST_TAGS_KEY = STORAGE_KEYS.costTags;

/** 界面展示的快捷标签数量上限 */
const TOP_N = 6;

/** 候选池中的单条费用名目及其频次 */
export interface CostTagEntry {
  name: string
  count: number
}

interface CostTagsState {
  /** 候选池（费用名目 → 使用频次），本地持久化 */
  list: CostTagEntry[]
}

/** 校验单条候选是否结构合法 */
function isValidEntry(e: unknown): e is CostTagEntry {
  return (
    typeof e === "object" &&
    e !== null &&
    typeof (e as CostTagEntry).name === "string" &&
    (e as CostTagEntry).name.length > 0 &&
    typeof (e as CostTagEntry).count === "number" &&
    (e as CostTagEntry).count >= 0
  );
}

/**
 * 费用明细学习标签 store
 *
 * 本地记录日记「花费明细」各名目的使用频次：
 * - App onLaunch 时 init 从 storage 恢复，无数据则以默认种子兜底
 * - 保存日记成功后 recordUsed 累计频次，首次名目自动入池
 * - getter topPresets 按频次降序（同名按字典序稳定）取前 TOP_N 供表单展示
 */
export const useCostTagsStore = defineStore("costTags", {
  state: (): CostTagsState => ({
    list: DEFAULT_COST_PRESETS.map((name) => ({ name, count: 1 })),
  }),

  getters: {
    /** 频次最高的 TOP_N 个费用名目（无数据时仍含默认种子，保证恒非空） */
    topPresets: (state): string[] =>
      [...state.list]
        .sort((a, b) => b.count - a.count || a.name.localeCompare(b.name, "zh"))
        .slice(0, TOP_N)
        .map((e) => e.name),
  },

  actions: {
    /** 初始化：从 storage 恢复；无数据/损坏则以默认种子兜底并持久化（App onLaunch 调用） */
    init() {
      const raw = uni.getStorageSync(COST_TAGS_KEY);
      if (raw) {
        try {
          const parsed = JSON.parse(raw) as unknown;
          const list = Array.isArray(parsed)
            ? parsed.filter(isValidEntry).map((e) => ({ name: e.name, count: Math.floor(e.count) }))
            : [];
          // 池被清空过（用户清 storage 或非法数据）时回退种子，保证有快捷项
          if (list.length > 0) {
            this.list = list;
            return;
          }
        } catch {
          // 忽略损坏的 storage，回退种子
        }
      }
      this.list = DEFAULT_COST_PRESETS.map((name) => ({ name, count: 1 }));
      this.persist();
    },

    /** 累计频次：本次实际用到的费用名目逐名 count +1，首次名目以 count 1 入池，随后持久化 */
    recordUsed(names: string[]) {
      if (!names || names.length === 0) return;
      for (const raw of names) {
        const name = (raw || "").trim();
        if (!name) continue;
        const hit = this.list.find((e) => e.name === name);
        if (hit) {
          hit.count += 1;
        } else {
          this.list.push({ name, count: 1 });
        }
      }
      this.persist();
    },

    /** 持久化当前候选池 */
    persist() {
      uni.setStorageSync(COST_TAGS_KEY, JSON.stringify(this.list));
    },
  },
});
