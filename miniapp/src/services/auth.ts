import { API_PREFIX, BASE_URL } from "@/config";
import { get, post, put } from "./request";
import { STORAGE_KEYS } from "@/constants/storage";

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
 * 上传头像（uni.uploadFile），返回可展示的相对 URL。
 * 需携带 X-Auth-Token；注意 content-type 由 uni.uploadFile 自动设置 multipart/form-data。
 */
export function uploadAvatar(tempPath: string): Promise<string> {
  const token = uni.getStorageSync(STORAGE_KEYS.token) as string;
  return new Promise((resolve, reject) => {
    uni.uploadFile({
      url: `${BASE_URL}${API_PREFIX}/upload/avatar`,
      filePath: tempPath,
      name: "file",
      header: token ? { 'X-Auth-Token': token } : {},
      success: (res) => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          try {
            const parsed = JSON.parse(res.data as string) as { url?: string; code?: number; data?: { url?: string } };
            const url = parsed.url ?? parsed.data?.url;
            if (url) {
              resolve(url);
            } else {
              reject(new Error("上传响应解析失败"));
            }
          } catch {
            reject(new Error("上传响应解析失败"));
          }
        } else {
          let detail = "上传失败";
          try {
            detail = (JSON.parse(res.data as string) as { detail?: string })?.detail || detail;
          } catch {
            /* ignore */
          }
          reject(new Error(detail));
        }
      },
      fail: (err) => reject(new Error(err.errMsg || "上传失败")),
    });
  });
}
