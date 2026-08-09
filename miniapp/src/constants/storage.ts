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
} as const;
