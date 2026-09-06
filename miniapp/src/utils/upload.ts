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

/**
 * 计算文件 MD5
 *
 * @param filePath 本地文件路径（uni.chooseMedia 返回的临时路径）
 * @returns MD5 十六进制字符串
 */
function computeFileMD5(filePath: string): Promise<string> {
  return new Promise((resolve, reject) => {
    const fs = uni.getFileSystemManager();
    fs.getFileInfo({
      filePath,
      digestAlgorithm: "md5",
      success(res) {
        resolve(res.digest as string);
      },
      fail: reject,
    });
  });
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

// ==================== 两步上传（预检 + 按需上传） ====================

/** 预检响应 */
export interface CheckResult {
  hit: boolean;
  safe?: boolean;
  url?: string;
}

/**
 * 文件秒传预检（MD5 + size 查询，不上传文件）
 *
 * @param md5Val 文件 MD5
 * @param sizeBytes 文件大小（字节）
 * @returns CheckResult
 */
export async function checkFile(md5Val: string, sizeBytes: number): Promise<CheckResult> {
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

/**
 * 两步上传：先预检 MD5，命中则零流量返回 URL，未命中则正常上传。
 *
 * @param filePath 本地文件路径
 * @param type 上传类型（gear-image / avatar）
 * @returns URL 字符串
 * @throws 图片内容可能包含违规信息，请检查后重试
 */
export async function uploadFileWithCheck(
  filePath: string,
  type: "gear-image" | "avatar",
): Promise<string> {
  // Step 1: 并行计算 MD5 + 获取文件大小
  const [fileMd5, fileSize] = await Promise.all([
    computeFileMD5(filePath),
    new Promise<number>((resolve, reject) => {
      uni.getFileSystemManager().getFileInfo({
        filePath,
        success: (info) => resolve(info.size),
        fail: reject,
      });
    }),
  ]);

  // Step 2: 预检
  try {
    const checkResult = await checkFile(fileMd5, fileSize);

    if (checkResult.hit && checkResult.safe && checkResult.url) {
      // 命中 + 安全通过，直接返回 URL
      return checkResult.url;
    }

    if (checkResult.hit && !checkResult.safe) {
      // 命中 + 安全不通过，抛出错误让上层处理
      throw new Error("图片内容可能包含违规信息，请检查后重试");
    }
  } catch (err) {
    // 安全检查不通过，直接向上抛出
    if ((err as Error).message === "图片内容可能包含违规信息，请检查后重试") {
      throw err;
    }
    // 其他错误静默忽略，继续上传
  }

  // Step 3: 未命中，正常上传
  const result = await uploadFile({
    path: `/upload/${type}`,
    filePath,
  });
  return result.url;
}
