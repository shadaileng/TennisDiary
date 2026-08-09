import { API_PREFIX, BASE_URL, REQUEST_TIMEOUT } from "@/config";
import { STORAGE_KEYS } from "@/constants/storage";
import { logError, logWarn } from "@/utils/eventLogger";

/**
 * 网络请求封装
 *
 * 统一处理 baseURL、JWT 注入、业务错误与 401 登出。
 * 通过 uni.request 实现，跨 H5 与小程序端保持一致。
 */

// ==================== 类型 ====================

/** 统一API响应格式 */
export interface ApiResponse<T = any> {
  code: number;
  message: string;
  success: boolean;
  data: T | null;
}

/** 业务错误（后端 detail 或网络/状态码错误） */
export class ApiError extends Error {
  /** HTTP 状态码（网络异常时为 -1） */
  status: number;
  /** 后端返回的 detail 或业务消息 */
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

export interface RequestOptions {
  /** 是否携带 Authorization（默认 true） */
  auth?: boolean
  /** 是否允许 401 触发登出（默认 true） */
  handle401?: boolean
  /** 超时（毫秒，默认 10000） */
  timeout?: number
  /** 自定义 header */
  headers?: Record<string, string>
}

// ==================== 常量 ====================

/** storage 键名统一从常量读取，避免魔法字符串 */
const TOKEN_KEY = STORAGE_KEYS.token;
const USER_KEY = STORAGE_KEYS.user;

// ==================== 工具 ====================

/**
 * 读取 token。直接读 storage 而非导入 auth store，
 * 避免 request 与 store 之间产生循环依赖。
 */
function getToken(): string {
  return (uni.getStorageSync(TOKEN_KEY) as string) || "";
}

/** 清理登录态（401 时调用） */
function clearAuth() {
  uni.removeStorageSync(TOKEN_KEY);
  uni.removeStorageSync(USER_KEY);
}

/** 登录引导 toast 节流间隔（毫秒），避免多请求/重复触发刷屏 */
const LOGIN_GUIDE_THROTTLE = 3000;
let lastLoginGuideAt = 0;

/** 弹出未登录引导提示（节流） */
function promptLogin() {
  const now = Date.now();
  if (now - lastLoginGuideAt < LOGIN_GUIDE_THROTTLE) return;
  lastLoginGuideAt = now;
  uni.showToast({ title: "请到「我的」页登录后使用", icon: "none" });
}

/**
 * 从后端错误响应中提取可展示的错误信息。
 *
 * 注意：success 回调中 res.errMsg 恒为 "request:ok"，与 HTTP 状态码无关，
 * 因此不能作为降级兜底，否则 4xx/5xx 会误提示 "request ok"。
 * 降级策略：detail/message → 非 JSON 文本 → 基于状态码的通用提示。
 */
function parseDetail(res: any): string {
  const data = res?.data;
  if (data && typeof data === "object") {
    // 优先使用新的统一响应格式
    if (typeof data.message === "string" && data.message.trim()) return data.message.trim();
    // 兼容旧格式
    const detail = data.detail;
    if (typeof detail === "string" && detail.trim()) return detail.trim();
    if (Array.isArray(detail) && detail.length) return JSON.stringify(detail);
  }
  if (typeof data === "string" && data.trim()) return data.trim();
  const status = res?.statusCode;
  return status != null && status >= 400 ? `请求失败（HTTP ${status}）` : "请求失败";
}

// ==================== 核心 ====================

function request<T>(method: "GET" | "POST" | "PUT" | "DELETE", url: string, data?: any, options: RequestOptions = {}): Promise<T> {
  const {
    auth = true,
    handle401 = true,
    timeout = REQUEST_TIMEOUT,
    headers = {},
  } = options;

  // 未登录门控：需要鉴权但本地无 token 时直接短路，不发起请求
  if (auth && !getToken()) {
    promptLogin();
    return Promise.reject(new ApiError(401, "请先登录"));
  }

  const fullUrl = url.startsWith("http") ? url : `${BASE_URL}${API_PREFIX}${url}`;

  const finalHeaders: Record<string, string> = { "Content-Type": "application/json", ...headers };
  if (auth) {
    const token = getToken();
    if (token) {
      finalHeaders.Authorization = `Bearer ${token}`;
    }
  }

  return new Promise<T>((resolve, reject) => {
    uni.request({
      url: fullUrl,
      method,
      data,
      header: finalHeaders,
      timeout,
      success: (res) => {
        const statusCode = res.statusCode;
        if (statusCode >= 200 && statusCode < 300) {
          // 处理统一响应格式
          const apiRes = res.data as ApiResponse<T>;
          if (apiRes && typeof apiRes === "object" && "code" in apiRes) {
            if (apiRes.code === 0) {
              resolve(apiRes.data as T);
            } else {
              // 业务错误
              if (apiRes.code === 10001 && handle401) {
                clearAuth();
                promptLogin();
              }
              logError(`API业务错误 ${method} ${url}: ${apiRes.message}`, {
                method,
                url,
                statusCode,
                code: apiRes.code,
              }, "api_error");
              reject(new ApiError(statusCode, apiRes.message || "请求失败"));
            }
          } else {
            // 兼容旧格式（直接返回数据）
            resolve(res.data as T);
          }
          return;
        }
        if (statusCode === 401 && handle401) {
          clearAuth();
          promptLogin();
        }
        reject(new ApiError(statusCode, parseDetail(res)));
      },
      fail: (err) => {
        logError(`网络请求失败 ${method} ${url}: ${err.errMsg || "未知错误"}`, {
          method,
          url,
          status: -1,
        }, "network_error");
        reject(new ApiError(-1, err.errMsg || "网络请求失败"));
      },
    });
  });
}

// ==================== 导出方法 ====================

export function get<T>(url: string, options?: RequestOptions): Promise<T> {
  return request<T>("GET", url, undefined, options);
}

export function post<T>(url: string, data?: any, options?: RequestOptions): Promise<T> {
  return request<T>("POST", url, data, options);
}

export function put<T>(url: string, data?: any, options?: RequestOptions): Promise<T> {
  return request<T>("PUT", url, data, options);
}

export function del<T>(url: string, options?: RequestOptions): Promise<T> {
  return request<T>("DELETE", url, undefined, options);
}
