import { defineStore } from "pinia";

import { getMe, login as loginApi } from "@/services/auth";
import type { User } from "@/types";

/** storage 键名，避免魔法字符串散落 */
export const TOKEN_KEY = "td_token";
export const USER_KEY = "td_user";

interface AuthState {
  token: string
  user: User | null
}

/**
 * 登录态管理 store
 *
 * 负责 token 与用户信息的持久化读写（uni.setStorageSync），
 * 并暴露登录/登出 action。Phase1-8 对接 /api/auth/login 后，
 * login() 内部改调服务层。
 */
export const useAuthStore = defineStore("auth", {
  state: (): AuthState => ({
    token: "",
    user: null,
  }),

  getters: {
    /** 是否已登录（存在 token） */
    isLoggedIn: (state): boolean => !!state.token,
  },

  actions: {
    /** 初始化：从 storage 恢复登录态（App onLaunch 调用） */
    init() {
      this.token = uni.getStorageSync(TOKEN_KEY) || "";
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
      uni.setStorageSync(TOKEN_KEY, token);
      uni.setStorageSync(USER_KEY, JSON.stringify(user));
    },

    /**
     * 登录入口：用 wx.login 的 code 换取 token，并获取用户信息。
     * 由网络层（services/auth.ts）调用后台 /api/auth/login 与 /api/auth/me。
     */
    async login(code: string) {
      const token = await loginApi({ code });
      // 换取 token 后再获取用户信息（需携带 Authorization）
      const user = await getMe();
      this.setAuth(token.access_token, user);
      return user;
    },

    /** 登出：清空内存态与持久化 */
    logout() {
      this.token = "";
      this.user = null;
      uni.removeStorageSync(TOKEN_KEY);
      uni.removeStorageSync(USER_KEY);
    },
  },
});
