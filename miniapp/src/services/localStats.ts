/**
 * 本地统计聚合（Step 129 游客数据总览本地化）
 *
 * 口径对齐后端 `/api/stats`：total_sessions=日记 count、total_duration=Σduration、
 * avg_intensity/avg_mood=均值(保留2位)、total_cost=Σ 日记 costs.amount、
 * total_gears=装备 count；游客无分析记录，total_analyses/avg_score 恒 0。
 */
import type { AnyDiary, AnyGear, Stats } from "@/types";

function round2(n: number): number {
  return Math.round(n * 100) / 100;
}

function mean(list: number[]): number {
  return list.length ? list.reduce((s, n) => s + n, 0) / list.length : 0;
}

function sumCostAmount(costs: { amount: number }[] | undefined): number {
  return (costs || []).reduce((s, c) => s + (Number(c.amount) || 0), 0);
}

/** 基于本地（缓存合并视图）数据实时聚合（口径对齐后端 /api/stats）
 * 入参为 diary/gear store 的合并视图（云端快照 + 离线待同步），
 * 仅读取统计所需公共字段，对 Diary/Gear 与 LocalXxx 均适用。 */
export function aggregateLocalStats(diaries: AnyDiary[], gears: AnyGear[]): Stats {
  const n = diaries.length;
  const total_duration = diaries.reduce((s, d) => s + (d.duration || 0), 0);
  const avg_intensity = n ? round2(mean(diaries.map((d) => d.intensity))) : 0;
  const avg_mood = n ? round2(mean(diaries.map((d) => d.mood))) : 0;
  const total_cost = round2(diaries.reduce((s, d) => s + sumCostAmount(d.costs), 0));
  return {
    total_sessions: n,
    total_duration,
    avg_intensity,
    avg_mood,
    total_cost,
    total_gears: gears.length,
    total_analyses: 0,
    avg_score: 0,
  };
}
