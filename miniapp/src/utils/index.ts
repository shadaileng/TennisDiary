/**
 * 前端通用工具函数
 *
 * 由原 Web 版 `docs/reference/tennis-diary/src/utils.ts` 迁移而来，
 * 仅保留纯前端通用工具（枚举、日期/金额格式化、聚合）。
 * Web 专属（DOM / Blob / Canvas 截图等）留待 Phase 5 / B2。
 */

import type { CostItem } from "@/types";

// ==================== 枚举常量 ====================

/** 强度 1-5 的 label + emoji */
export const INTENSITY = [
  { v: 1, label: "很轻", emoji: "🌱" },
  { v: 2, label: "轻松", emoji: "😊" },
  { v: 3, label: "适中", emoji: "💪" },
  { v: 4, label: "较累", emoji: "🥵" },
  { v: 5, label: "极限", emoji: "🔥" },
] as const;

/** 心情 1-5 的 label + emoji */
export const MOOD = [
  { v: 1, label: "糟糕", emoji: "😫" },
  { v: 2, label: "不太好", emoji: "😕" },
  { v: 3, label: "一般", emoji: "😐" },
  { v: 4, label: "不错", emoji: "😄" },
  { v: 5, label: "很棒", emoji: "🤩" },
] as const;

/** 训练/比赛类型 */
export const SESSION_TYPES = ["训练", "比赛", "发球机", "发球练习"] as const;
/** 装备分类 */
export const GEAR_CATEGORIES = ["球拍", "球鞋", "衣服", "袜子", "帽子", "毛巾", "网球", "其他"] as const;
/** 动作分析种类 */
export const ANALYSIS_KINDS = ["综合", "正手", "反手", "截击", "发球", "高压"] as const;

// ==================== 日期 / 时间 ====================

/** 两位数补零 */
export function pad(n: number): string {
  return n < 10 ? `0${n}` : `${n}`;
}

/** 今天的日期字符串 YYYY-MM-DD */
export function todayStr(): string {
  const d = new Date();
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

/** 当前时间字符串 HH:mm */
export function nowTimeStr(): string {
  const d = new Date();
  return `${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

/** 最近 n 天的日期数组（含今天，升序） */
export function lastNDays(n: number): string[] {
  const out: string[] = [];
  const d = new Date();
  for (let i = n - 1; i >= 0; i--) {
    const t = new Date(d);
    t.setDate(d.getDate() - i);
    out.push(`${t.getFullYear()}-${pad(t.getMonth() + 1)}-${pad(t.getDate())}`);
  }
  return out;
}

/** 日期所在星期几，如「周三」 */
export function weekdayCN(dateStr: string): string {
  const wd = ["日", "一", "二", "三", "四", "五", "六"];
  return `周${wd[new Date(dateStr + "T00:00:00").getDay()]}`;
}

/** 日期字符串的月份键 YYYY-MM */
export function monthKey(dateStr: string): string {
  return dateStr.slice(0, 7);
}

// ==================== 格式化 ====================

/** 时长格式化：90 → "1小时30分" */
export function fmtDuration(min: number): string {
  if (min < 60) return `${min}分钟`;
  const h = Math.floor(min / 60);
  const m = min % 60;
  return m ? `${h}小时${m}分` : `${h}小时`;
}

/** 金额格式化：整数 ¥8，小数保留两位 */
export function fmtMoney(n: number): string {
  return n % 1 === 0 ? `¥${n}` : `¥${n.toFixed(2)}`;
}

// ==================== 聚合 ====================

/** 花费明细合计 */
export function sumCosts(costs: CostItem[]): number {
  return costs.reduce((s, c) => s + (Number(c.amount) || 0), 0);
}
