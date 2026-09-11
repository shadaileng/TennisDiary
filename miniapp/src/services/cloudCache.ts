/**
 * 登录态云端快照缓存（Step 141）
 *
 * 账号隔离地缓存「最近一次成功拉取的云端列表」，作为登录态列表/详情渲染的唯一数据源之一。
 * 列表缓存：`td_cache_{userId}_{entity}` → `{ updatedAt, list }`（entity：diaries/gears/weights/analyses）
 * 分析详情：按 id 单条缓存 `td_cache_{userId}_analysis_{id}`，LRU 上限 20 条（索引键 `td_cache_{userId}_analysis_index`）
 *
 * 零 store 依赖，store 会 import 本模块。损坏容错沿用 storageBase。
 */

import { loadRaw, persist } from "@/services/storageBase";
import { analysisDetailKey, analysisIndexKey, cacheKey } from "@/constants/storage";
import type { Analysis, Diary, Gear, WeightRecord } from "@/types";

/** 列表缓存信封：记录写入时间戳，便于排查/未来增量 */
export interface CacheEnvelope<T> {
  updatedAt: number;
  list: T[];
}

/** 分析详情 LRU 上限 */
const ANALYSIS_DETAIL_MAX = 20;

type ListEntity = "diaries" | "gears" | "weights" | "analyses";

function getList<T>(userId: number, entity: ListEntity): T[] {
  const env = loadRaw<CacheEnvelope<T>>(cacheKey(userId, entity));
  return env?.list ?? [];
}

function setList<T>(userId: number, entity: ListEntity, list: T[]): void {
  // 云端快照为 best-effort 缓存：写不下（超容量/异常）静默丢弃，绝不弹 toast 打扰浏览
  persist(cacheKey(userId, entity), { updatedAt: Date.now(), list } satisfies CacheEnvelope<T>, { silent: true });
}

function getUpdatedAt(userId: number, entity: ListEntity): number {
  return loadRaw<CacheEnvelope<unknown>>(cacheKey(userId, entity))?.updatedAt ?? 0;
}

// ==================== 日记 / 装备 / 体重 列表 ====================

export function getCloudDiaries(userId: number): Diary[] {
  return getList<Diary>(userId, "diaries");
}
export function setCloudDiaries(userId: number, list: Diary[]): void {
  setList(userId, "diaries", list);
}

export function getCloudGears(userId: number): Gear[] {
  return getList<Gear>(userId, "gears");
}
export function setCloudGears(userId: number, list: Gear[]): void {
  setList(userId, "gears", list);
}

export function getCloudWeights(userId: number): WeightRecord[] {
  return getList<WeightRecord>(userId, "weights");
}
export function setCloudWeights(userId: number, list: WeightRecord[]): void {
  setList(userId, "weights", list);
}

// ==================== 分析列表 / 详情 ====================

export function getAnalysesCache(userId: number): Analysis[] {
  return getList<Analysis>(userId, "analyses");
}
/**
 * 写入分析列表缓存。仅保留列表渲染所需轻量字段（剥离 report/pose/highlights/video_url），
 * 并把 dataURL 封面丢弃（离线统一显示占位图），避免快照体积超限导致缓存写不进。
 */
export function setAnalysesCache(userId: number, list: Analysis[]): void {
  setList(userId, "analyses", list.map(toListCache));
}
export function getAnalysesCacheUpdatedAt(userId: number): number {
  return getUpdatedAt(userId, "analyses");
}

/** 取单条分析详情（缓存命中）；未命中返回 null（调用方决定是否在线拉取） */
export function getAnalysisDetail(userId: number, id: number): Analysis | null {
  return loadRaw<Analysis>(analysisDetailKey(userId, id));
}

/**
 * 写入单条分析详情并维护 LRU 索引（超出上限淘汰最久未访问）。
 * 详情保留 report/pose 等文字报告字段（离线可读），仅丢弃 dataURL 封面（离线本就看不了）。
 * 写入静默：超容量时直接丢弃该条缓存，不弹提示。
 */
export function setAnalysisDetail(userId: number, analysis: Analysis): void {
  const slim: Analysis = { ...analysis, thumb: stripDataUrl(analysis.thumb) };
  persist(analysisDetailKey(userId, analysis.id), slim, { silent: true });
  const idxKey = analysisIndexKey(userId);
  const idx = loadRaw<number[]>(idxKey) ?? [];
  const next = [analysis.id, ...idx.filter((x) => x !== analysis.id)];
  if (next.length > ANALYSIS_DETAIL_MAX) {
    const evicted = next.splice(ANALYSIS_DETAIL_MAX);
    for (const id of evicted) uni.removeStorageSync(analysisDetailKey(userId, id));
  }
  persist(idxKey, next, { silent: true });
}

/** 丢弃 dataURL 封面（离线下本就看不了，留着只会撑大缓存） */
function stripDataUrl(thumb?: string): string | undefined {
  return thumb && !thumb.startsWith("data:") ? thumb : undefined;
}

/** 列表缓存裁剪：只留列表渲染所需字段，剔除 report/pose/highlights/video_url 等大字段 */
function toListCache(a: Analysis): Analysis {
  return {
    id: a.id,
    date: a.date,
    kind: a.kind,
    mode: a.mode,
    score: a.score,
    summary: a.summary,
    created_at: a.created_at,
    status: a.status,
    thumb: stripDataUrl(a.thumb),
    pose: a.pose ? ({ detected: a.pose.detected } as Analysis["pose"]) : undefined,
  };
}
