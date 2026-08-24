/**
 * 统一文件上传工具
 *
 * 封装 uni.uploadFile，统一处理 Token 注入、响应解析、错误处理与进度回调。
 * - uploadRaw<T>：底层实现，解析完整 data 并透出 mirage（视频等复杂响应用）
 * - uploadFile：图片类便捷封装，返回 { url, mirage }
 *
 * 事件钩子（onSuccess / onFailed / onMirage）由调用方按需传入，
 * 对应埋点由调用方自行处理（不在此层耦合 eventLogger）。
 */

import { API_PREFIX, BASE_URL } from "@/config";
import { STORAGE_KEYS } from "@/constants/storage";

// ==================== 类型 ====================

/** 上传选项 */
export interface UploadOptions {
  /** 相对路径，如 '/upload/avatar' */
  path: string;
  /** 临时文件路径（uni.chooseMedia 返回） */
  filePath: string;
  /** 额外表单字段 */
  formData?: Record<string, string>;
  /** 文件字段名，默认 'file' */
  fieldName?: string;
  /** 超时毫秒，默认 60000 */
  timeout?: number;
  /** 进度回调 */
  onProgress?: (p: { percent: number; transferred: number; total: number }) => void;
}

/** 图片类上传结果 */
export interface UploadResult {
  url: string;
  mirage: boolean;
}

/** 事件钩子（图片/视频统一签名） */
export interface UploadHooks<T = any> {
  onSuccess?: (result: T, durationMs: number) => void;
  onFailed?: (error: Error, durationMs: number) => void;
  onMirage?: (result: T, durationMs: number) => void;
}

// ==================== 工具函数 ====================

function getToken(): string {
  return (uni.getStorageSync(STORAGE_KEYS.token) as string) || "";
}

/** 解析上传失败响应 detail */
function parseError(raw: string): string {
  try {
    const parsed = JSON.parse(raw) as { detail?: string; message?: string };
    return parsed.detail || parsed.message || "上传失败";
  } catch {
    return "上传失败";
  }
}

// ==================== 底层实现 ====================

/**
 * 底层上传：解析完整 data，透出 mirage。
 * 供 uploadFile（图片类）和 uploadVideo（视频类）共用。
 */
export function uploadRaw<T = any>(options: UploadOptions & UploadHooks<T>): Promise<T & { mirage?: boolean }> {
  const {
    path,
    filePath,
    formData = {},
    fieldName = "file",
    timeout = 60000,
    onProgress,
    onSuccess,
    onFailed,
    onMirage,
  } = options;

  const startTime = Date.now();

  return new Promise<T & { mirage?: boolean }>((resolve, reject) => {
    const task = uni.uploadFile({
      url: `${BASE_URL}${API_PREFIX}${path}`,
      filePath,
      name: fieldName,
      formData,
      timeout,
      header: { "X-Auth-Token": getToken() },
      success: (res) => {
        const durationMs = Date.now() - startTime;
        if (res.statusCode < 200 || res.statusCode >= 300) {
          const err = new Error(parseError(res.data as string));
          onFailed?.(err, durationMs);
          reject(err);
          return;
        }
        try {
          const parsed = JSON.parse(res.data as string) as {
            code: number;
            data?: T;
            message?: string;
          };
          if (parsed.code !== 0 || !parsed.data) {
            const err = new Error(parsed.message || "上传响应解析失败");
            onFailed?.(err, durationMs);
            reject(err);
            return;
          }
          const result = { ...parsed.data, mirage: (parsed.data as any)?.mirage ?? false } as T & { mirage?: boolean };
          if (result.mirage) {
            onMirage?.(result, durationMs);
          } else {
            onSuccess?.(result, durationMs);
          }
          resolve(result);
        } catch {
          const err = new Error("上传响应解析失败");
          onFailed?.(err, Date.now() - startTime);
          reject(err);
        }
      },
      fail: (err) => {
        const durationMs = Date.now() - startTime;
        const error = new Error(err.errMsg || "上传失败");
        onFailed?.(error, durationMs);
        reject(error);
      },
    });
    if (onProgress) {
      task.onProgressUpdate((r) =>
        onProgress({
          percent: r.progress,
          transferred: r.totalBytesSent,
          total: r.totalBytesExpectedToSend,
        }),
      );
    }
  });
}

/**
 * 图片类上传便捷封装（头像/装备图）。
 * 返回 { url, mirage }，与后端响应格式对齐。
 */
export function uploadFile(options: UploadOptions & UploadHooks<{ url?: string }>): Promise<UploadResult> {
  return uploadRaw<{ url?: string }>(options).then((data) => ({
    url: data.url as string,
    mirage: data.mirage ?? false,
  }));
}
