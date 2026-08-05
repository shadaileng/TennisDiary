import { get, post } from "./request";

import type { LoginRequest, Token, User } from "@/types";

/**
 * 认证相关 API
 *
 * 对接后台：
 * - POST /api/auth/login  微信登录（返回 Token）
 * - GET  /api/auth/me     获取当前用户（需 JWT）
 */

/**
 * 获取登录临时 code（wx.login）。
 *
 * - 小程序端：调用 `uni.login` 获取微信 code（5 分钟有效）
 * - H5 端：无微信环境，返回 mock code 用于后端接口联调
 */
export function getLoginCode(): Promise<string> {
  return new Promise((resolve, reject) => {
    uni.login({
      provider: "weixin",
      success: (res) => resolve(res.code),
      fail: (err) => reject(new Error(err.errMsg || "wx.login 失败")),
    });
  });
}

/** 微信登录：用 wx.login 的 code 换取 JWT */
export function login(data: LoginRequest): Promise<Token> {
  // 登录接口无需携带 Authorization
  return post<Token>("/auth/login", data, { auth: false });
}

/** 获取当前登录用户 */
export function getMe(): Promise<User> {
  return get<User>("/auth/me");
}
