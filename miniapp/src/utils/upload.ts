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

import type { ChunkPlan } from "./chunkUpload";

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
  /** 任务句柄回调（供调用方 abort，如「取消上传」） */
  onTask?: (task: UniApp.UploadTask) => void;
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

/** 以 URL 为交付物的钩子（头像/装备图/视频秒传埋点用） */
export type UploadUrlHooks = {
  onSuccess?: (url: string, durationMs: number) => void;
  onFailed?: (error: Error, durationMs: number) => void;
  onMirage?: (url: string, durationMs: number) => void;
};

// ==================== 工具函数 ====================

function getToken(): string {
  return (uni.getStorageSync(STORAGE_KEYS.token) as string) || "";
}

/** 指纹计算超时（毫秒）：低端机大文件可能很慢，超时静默退回整体上传 */
const FINGERPRINT_TIMEOUT_MS = 10000;
/** 超过该体积不做指纹计算（200MB） */
export const FINGERPRINT_MAX_SIZE = 200 * 1024 * 1024;

/** 文件指纹：一次 getFileInfo 同时取 MD5 与大小 */
export interface FileFingerprint {
  md5: string;
  size: number;
  durationMs: number;
}

/**
 * 计算文件指纹（MD5 + 大小）
 *
 * 一次 `getFileInfo({digestAlgorithm:'md5'})` 同时拿到 digest 与 size，
 * 避免两次读文件；带超时兜底，超时后由调用方静默退回整体上传。
 */
export function getFileFingerprint(
  filePath: string,
  timeoutMs: number = FINGERPRINT_TIMEOUT_MS,
): Promise<FileFingerprint> {
  const startedAt = Date.now();
  return new Promise<FileFingerprint>((resolve, reject) => {
    let settled = false;
    const timer = setTimeout(() => {
      if (settled) return;
      settled = true;
      reject(new Error("文件指纹计算超时"));
    }, timeoutMs);

    uni.getFileSystemManager().getFileInfo({
      filePath,
      digestAlgorithm: "md5",
      success: (res: any) => {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        resolve({
          md5: (res?.digest as string) || "",
          size: Number(res?.size) || 0,
          durationMs: Date.now() - startedAt,
        });
      },
      fail: (err: any) => {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        reject(new Error(err?.errMsg || "文件信息读取失败"));
      },
    });
  });
}

/**
 * 按文件大小推导上传超时（毫秒）：每 MB 约 3s，夹在 120s ~ 300s 之间。
 * 大视频弱网下 60s 默认超时必失败，这里按体积自适应。
 */
export function resolveUploadTimeout(sizeBytes: number): number {
  const sizeMb = (Number(sizeBytes) || 0) / (1024 * 1024);
  const raw = Math.round(sizeMb * 3000);
  return Math.min(Math.max(raw, 120000), 300000);
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
    onTask,
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
    onTask?.(task);
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

// ==================== 两步上传（预检 + 按需上传） ====================

/** 预检响应 */
export interface CheckResult {
  hit: boolean;
  safe?: boolean;
  url?: string;
  /** 命中记录的 file_id（137：秒传与正常上传统一交付 file_id） */
  file_id?: number;
  /** 未命中且 category=video 时下发的分片策略与会话进度（140） */
  chunk?: ChunkPlan;
}

/**
 * 文件秒传预检（MD5 + size 查询，不上传文件）
 *
 * @param md5Val 文件 MD5
 * @param sizeBytes 文件大小（字节）
 * @param category 可选来源隔离（video / gear_image / avatar），不传行为不变
 * @returns CheckResult
 */
export async function checkFile(
  md5Val: string,
  sizeBytes: number,
  category?: string,
): Promise<CheckResult> {
  const res = await new Promise<CheckResult>((resolve, reject) => {
    uni.request({
      url: `${BASE_URL}${API_PREFIX}/upload/check`,
      method: "POST",
      header: {
        "X-Auth-Token": getToken(),
        "content-type": "application/json",
      },
      data: {
        md5: md5Val,
        size_bytes: sizeBytes,
        ...(category ? { category } : {}),
      },
      success: (r) => {
        if (r.statusCode < 200 || r.statusCode >= 300) {
          reject(new Error("预检失败"));
          return;
        }
        const data = r.data as { code: number; data?: CheckResult };
        if (data.code !== 0 || !data.data) {
          reject(new Error(data.code !== 0 ? "预检失败" : "预检响应解析失败"));
          return;
        }
        resolve(data.data);
      },
      fail: (err) => reject(new Error(err.errMsg || "预检请求失败")),
    });
  });

  return res;
}

const UNSAFE_IMAGE_MSG = "图片内容可能包含违规信息，请检查后重试";

/** 上传类型 → 后端 upload_source（预检按来源隔离，避免跨分类误命中） */
const CATEGORY_BY_TYPE: Record<"gear-image" | "avatar", string> = {
  "gear-image": "gear_image",
  avatar: "avatar",
};

/**
 * 两步上传：先预检 MD5，命中则零流量返回 URL，未命中则正常上传。
 *
 * @param filePath 本地文件路径
 * @param type 上传类型（gear-image / avatar）
 * @param hooks 可选事件钩子（命中秒传时触发 onMirage）
 * @returns URL 字符串
 * @throws 图片内容可能包含违规信息，请检查后重试
 */
export async function uploadFileWithCheck(
  filePath: string,
  type: "gear-image" | "avatar",
  hooks?: UploadUrlHooks,
): Promise<string> {
  const startTime = Date.now();

  // Step 1: 一次 getFileInfo 取 MD5 + size（超时/失败静默退回上传）
  let fileMd5 = "";
  let fileSize = 0;
  try {
    const fp = await getFileFingerprint(filePath);
    fileMd5 = fp.md5;
    fileSize = fp.size;
  } catch {
    // 指纹不可用时不影响正确性，仅失去秒传机会
  }

  // Step 2: 预检（按来源隔离）
  if (fileMd5) {
    try {
      const checkResult = await checkFile(fileMd5, fileSize, CATEGORY_BY_TYPE[type]);

      if (checkResult.hit && checkResult.safe && checkResult.url) {
        hooks?.onMirage?.(checkResult.url, Date.now() - startTime);
        return checkResult.url;
      }

      if (checkResult.hit && !checkResult.safe) {
        const err = new Error(UNSAFE_IMAGE_MSG);
        hooks?.onFailed?.(err, Date.now() - startTime);
        throw err;
      }
    } catch (err) {
      // 安全检查不通过，直接向上抛出
      if ((err as Error).message === UNSAFE_IMAGE_MSG) {
        throw err;
      }
      // 其他错误静默忽略，继续上传
    }
  }

  // Step 3: 未命中，正常上传
  const result = await uploadFile({
    path: `/upload/${type}`,
    filePath,
    onSuccess: hooks?.onSuccess
      ? (res) => hooks.onSuccess?.((res.url as string) || "", Date.now() - startTime)
      : undefined,
    onMirage: hooks?.onMirage
      ? (res) => hooks.onMirage?.((res.url as string) || "", Date.now() - startTime)
      : undefined,
    onFailed: hooks?.onFailed,
  });
  return result.url;
}
