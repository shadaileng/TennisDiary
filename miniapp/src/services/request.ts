import { API_PREFIX, BASE_URL, REQUEST_TIMEOUT } from "@/config";
import { STORAGE_KEYS } from "@/constants/storage";

/**
 * 网络请求封装
 *
 * 统一处理 baseURL、JWT 注入、业务错误与 401 登出。
 * 通过 uni.request 实现，跨 H5 与小程序端保持一致。
 */

// ==================== 类型 ====================

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

/** 解析错误消息：优先取后端 detail/message，其次 errMsg */
function parseDetail(res: any): string {
  return (
    (res?.data?.detail) ||
    (res?.data?.message) ||
    (res?.errMsg) ||
    "请求失败"
  );
}

// ==================== 核心 ====================

function request<T>(method: "GET" | "POST" | "PUT" | "DELETE", url: string, data?: any, options: RequestOptions = {}): Promise<T> {
  const {
    auth = true,
    handle401 = true,
    timeout = REQUEST_TIMEOUT,
    headers = {},
  } = options;

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
          resolve(res.data as T);
          return;
        }
        if (statusCode === 401 && handle401) {
          clearAuth();
          uni.showToast({ title: "登录已过期，请重新登录", icon: "none" });
        }
        reject(new ApiError(statusCode, parseDetail(res)));
      },
      fail: (err) => {
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
