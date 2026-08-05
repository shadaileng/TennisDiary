import { defineStore } from "pinia";

import type { Token, User } from "@/types";

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
     * 登录入口。Phase1-7 网络层与登录服务封装完成后，
     * 此处改为调用 services/auth.ts 的 login()。
     */
    async login(_code: string) {
      // TODO(Phase1-8): 调用 /api/auth/login 换取 token 与用户
      throw new Error("登录服务未接入，待 Phase1-8 实现");
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
