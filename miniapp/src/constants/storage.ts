/**
 * 本地 storage 键名统一收口。
 * 统一使用 `td_` 前缀，避免散落各处导致命名冲突或遗漏。
 */
export const STORAGE_KEYS = {
  /** 登录 token */
  token: "td_token",
  /** 用户信息 */
  user: "td_user",
  /** 全局偏好设置 */
  settings: "td_settings",
} as const;
