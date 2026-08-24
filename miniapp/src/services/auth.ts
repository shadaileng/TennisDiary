import { get, post, put } from "./request";
import { uploadFile } from "@/utils/upload";

import type { LoginRequest, LoginResponse, User, UserUpdate } from "@/types";

/**
 * 认证相关 API
 *
 * 对接后台：
 * - POST /api/auth/login  微信登录（返回 Token + User）
 * - GET  /api/auth/me     获取当前用户（需 JWT）
 * - PUT  /api/auth/me     更新用户资料（需 JWT）
 * - POST /api/upload/avatar 上传头像（需 JWT）
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

/** 微信登录：用 wx.login 的 code 换取 JWT + 用户信息 */
export function login(data: LoginRequest): Promise<LoginResponse> {
  // 登录接口无需携带鉴权头；401 属登录失败，交由调用方展示，不触发全局登出引导
  return post<LoginResponse>("/auth/login", data, { auth: false, handle401: false });
}

/** 获取当前登录用户 */
export function getMe(): Promise<User> {
  return get<User>("/auth/me");
}

/** 更新用户资料（昵称/头像） */
export function updateProfile(data: UserUpdate): Promise<{ user: User }> {
  return put<{ user: User }>("/auth/me", data);
}

/**
 * 上传头像，返回可展示的相对 URL。
 * 内部使用 uploadFile 统一上传工具，事件钩子由调用方按需注入。
 */
export function uploadAvatar(
  tempPath: string,
  hooks?: { onSuccess?: (url: string, durationMs: number) => void; onFailed?: (error: Error, durationMs: number) => void; onMirage?: (url: string, durationMs: number) => void },
): Promise<string> {
  return uploadFile({
    path: "/upload/avatar",
    filePath: tempPath,
    onSuccess: (data, durationMs) => hooks?.onSuccess?.(data.url as string, durationMs),
    onFailed: (error, durationMs) => hooks?.onFailed?.(error, durationMs),
    onMirage: (data, durationMs) => hooks?.onMirage?.(data.url as string, durationMs),
  }).then((r) => r.url);
}
