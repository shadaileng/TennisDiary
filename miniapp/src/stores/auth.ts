import { defineStore } from "pinia";

import { STORAGE_KEYS } from "@/constants/storage";
import { getLoginCode, login as loginApi } from "@/services/auth";
import type { User } from "@/types";
import { isLoggedIn as isTokenValid } from "@/utils/jwt";
import { createTraceId, logError, logInfo } from "@/utils/eventLogger";

function getCurrentPage(): string {
  try {
    const pages = getCurrentPages();
    return pages[pages.length - 1]?.route || "";
  } catch {
    return "";
  }
}

/** storage 键名统一从常量读取 */
const TOKEN_KEY = STORAGE_KEYS.token;
const USER_KEY = STORAGE_KEYS.user;
const HAS_LOGGED_IN_KEY = STORAGE_KEYS.hasLoggedIn;

interface AuthState {
  token: string
  user: User | null
  /** 是否曾登录（仅用于清理旧数据，不再作为登录判断依据） */
  hasLoggedIn: boolean
}

/**
 * 登录态管理 store
 *
 * 负责 token 与用户信息的持久化读写（uni.setStorageSync），
 * 并暴露登录/登出 action。Phase1-8 对接 /api/auth/login 后，
 * login() 内部改调服务层。
 *
 * 游客模式（Step 35）：登录态基于「token 有效（存在且未过期）」判断，
 * 未登录即为游客（isGuest），业务页不发请求并展示游客引导。
 */
export const useAuthStore = defineStore("auth", {
  state: (): AuthState => ({
    token: "",
    user: null,
    hasLoggedIn: false,
  }),

  getters: {
    /** 是否已登录：本地 token 有效（存在且未过期） */
    isLoggedIn: (state): boolean => isTokenValid(state.token),
    /** 是否为游客：未登录或 token 已失效 */
    isGuest: (state): boolean => !isTokenValid(state.token),
  },

  actions: {
    /** 初始化：从 storage 恢复登录态（App onLaunch 调用） */
    init() {
      this.token = uni.getStorageSync(TOKEN_KEY) || "";
      this.hasLoggedIn = !!uni.getStorageSync(HAS_LOGGED_IN_KEY);
      const raw = uni.getStorageSync(USER_KEY);
      if (raw) {
        try {
          this.user = JSON.parse(raw) as User;
        } catch {
          this.user = null;
        }
      }
    },

    /** 设置登录态并持久化（Phase1-8 登录成功后调用） */
    setAuth(token: string, user: User) {
      this.token = token;
      this.user = user;
      this.hasLoggedIn = true;
      uni.setStorageSync(TOKEN_KEY, token);
      uni.setStorageSync(USER_KEY, JSON.stringify(user));
      uni.setStorageSync(HAS_LOGGED_IN_KEY, true);
    },

    /**
     * 完整登录链路：wx.login 取 code → 换 token + user → 一次持久化。
     * 后端 /api/auth/login 一次返回 { access_token, user, is_new }，
     * 避免「先拿 token 再 getMe」的未登录短路 bug（Step 38）。
     */
    async login() {
      const traceId = createTraceId();
      try {
        logInfo("开始登录", { trace_id: traceId }, "login_start");
        const code = await getLoginCode();
        const result = await loginApi({ code });
        this.setAuth(result.access_token, result.user);
        logInfo("登录成功", { trace_id: traceId, is_new: result.is_new }, "login_success");
        return result.user;
      } catch (e) {
        logError("登录失败", { trace_id: traceId, error: (e as Error).message }, "login_failed");
        throw e;
      }
    },

    /** 资料更新后同步本地 user 缓存 */
    updateUser(user: User) {
      const traceId = createTraceId();
      logInfo("更新个人资料", { trace_id: traceId }, "profile_update");
      this.user = user;
      uni.setStorageSync(USER_KEY, JSON.stringify(user));
    },

    /**
     * 静默续登：仅在本地已有有效 token（但可能失效/需刷新）时才尝试重新登录；
     * 从未登录或已登出（无有效 token）则保持游客态，不请求后台。
     * 供 App.onLaunch 可选调用。失败时清空登录态。
     */
    async ensureLogin() {
      // 已有有效 token 直接返回；无有效 token（游客态）则不静默登录
      if (this.isLoggedIn || !this.token) {
        return;
      }
      try {
        await this.login();
      } catch (e) {
        console.error("静默登录失败", e);
        this.logout();
      }
    },

    /** 登出：清空内存态与持久化（含「曾登录」旧标志） */
    logout() {
      this.token = "";
      this.user = null;
      this.hasLoggedIn = false;
      uni.removeStorageSync(TOKEN_KEY);
      uni.removeStorageSync(USER_KEY);
      uni.removeStorageSync(HAS_LOGGED_IN_KEY);
    },
  },
});
