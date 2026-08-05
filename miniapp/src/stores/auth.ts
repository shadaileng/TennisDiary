import { defineStore } from "pinia";

import { STORAGE_KEYS } from "@/constants/storage";
import { getLoginCode, getMe, login as loginApi } from "@/services/auth";
import type { User } from "@/types";

/** storage 键名统一从常量读取 */
const TOKEN_KEY = STORAGE_KEYS.token;
const USER_KEY = STORAGE_KEYS.user;

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
     * 完整登录链路：wx.login 取 code → 换 token → 取用户 → 持久化。
     * 失败时清空登录态并抛出错误，由调用方决定提示方式。
     */
    async login() {
      const code = await getLoginCode();
      const token = await loginApi({ code });
      // 换取 token 后再获取用户信息（需携带 Authorization）
      const user = await getMe();
      this.setAuth(token.access_token, user);
      return user;
    },

    /**
     * 静默登录：已登录则直接返回；否则自动完成登录链路。
     * 供 App.onLaunch 调用。失败时提示并保持未登录态。
     */
    async ensureLogin() {
      if (this.isLoggedIn) {
        return;
      }
      try {
        await this.login();
      } catch (e) {
        const msg = e instanceof Error ? e.message : "登录失败";
        console.error("静默登录失败", e);
        this.logout();
        uni.showToast({ title: msg, icon: "none" });
      }
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
