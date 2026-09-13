/**
 * 本地 storage 键名统一收口。
 * 统一使用 `td_` 前缀，避免散落各处导致命名冲突或遗漏。
 */
export const STORAGE_KEYS = {
  /** 登录 token */
  token: "td_token",
  /** 用户信息 */
  user: "td_user",
  /** 是否曾登录（Step 35 起不再作为登录判断依据，仅用于清理旧数据） */
  hasLoggedIn: "td_has_logged_in",
  /** 全局偏好设置 */
  settings: "td_settings",
  /** 待上报的离线事件日志（上报失败时缓存，启动时补发） */
  eventLogPending: "td_event_log_pending",
  /** 费用明细学习标签候选池（高频名目 + 频次，本地持久化） */
  costTags: "td_cost_tags",
  /** 本地待同步日记（游客态本地 storage，Step 129） */
  pendingDiaries: "td_pending_diaries",
  /** 本地待同步装备（游客态本地 storage，Step 129） */
  pendingGears: "td_pending_gears",
  /** 本地待同步体重记录（游客态本地 storage，Step 129） */
  pendingWeights: "td_pending_weights",
  /** 有分析正在启动中（上传阶段 analysis 记录尚未创建，Step 139） */
  pendingAnalysisAt: "td_pending_analysis_at",
} as const;

/**
 * 登录态离线仓库 / 云端快照缓存的账号隔离键生成（Step 141）。
 * 全部收口 `td_` 前缀，按 userId 隔离，避免换号/登出串数据。
 */

/** 离线待同步仓库键（td_offline_{userId}_{entity}） */
export function offlineKey(userId: number, entity: "diaries" | "gears" | "weights"): string {
  return `td_offline_${userId}_${entity}`;
}

/** 云端快照缓存键（td_cache_{userId}_{entity}） */
export function cacheKey(userId: number, entity: "diaries" | "gears" | "weights" | "analyses"): string {
  return `td_cache_${userId}_${entity}`;
}
