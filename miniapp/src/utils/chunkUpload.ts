/**
 * 视频分片上传（140 方案 C+：单文件定位写 + manifest 登记）
 *
 * 服务端形态：
 * - 每片按 `offset = index * chunkSize` 由服务端定位写入 `data.bin`
 * - 片级校验（length 强制 + crc32 可选）通过才入账 `ok`，失败入 `failed`
 * - 整文件 MD5 校验通过后才登记为受管文件（免合并）
 *
 * 本模块职责：切片读盘 → 片级摘要 → 串行上传（单片失败重试 2 次）→ complete。
 * 续传依据完全来自服务端下发的 `uploaded` / `failed` / `missing`，本地不记账。
 */

import { ApiError } from "@/services/request";
import { completeChunkUpload, fetchChunkProgress } from "@/services/data";
import { crc32Of } from "./crc32";
import { resolveUploadTimeout, uploadRaw } from "./upload";

// ==================== 类型 ====================

/** 分片策略与会话进度（`/upload/check` 下发，服务端单一真源） */
export interface ChunkPlan {
  enabled: boolean;
  /** 单片大小（字节） */
  sizeBytes: number;
  /** 走分片的大小阈值（字节） */
  thresholdBytes: number;
  maxCount: number;
  /** 服务端是否接受片级 crc32 */
  crc32: boolean;
  /** 服务端会话已知的总片数（首次为 0） */
  total: number;
  /** 服务端会话已知的总字节（首次为 0） */
  totalSize: number;
  /** 服务端会话片大小（首次为 0） */
  chunkSize: number;
  /** 已入账 ok 的段（可跳过） */
  uploaded: number[];
  /** 校验失败入账的段（需重传） */
  failed: number[];
  /** 未登记段（需上传） */
  missing: number[];
}

/** 服务端未下发 chunk 时的兜底缺省值 */
export const CHUNK_DEFAULTS = {
  sizeBytes: 5 * 1024 * 1024,
  thresholdBytes: 20 * 1024 * 1024,
  maxCount: 512,
  crc32: true,
} as const;

/** 归一化服务端下发的 chunk（字段缺失时按缺省兜底） */
export function normalizeChunkPlan(raw?: Partial<ChunkPlan> | null): ChunkPlan {
  return {
    enabled: raw?.enabled ?? false,
    sizeBytes: raw?.sizeBytes || CHUNK_DEFAULTS.sizeBytes,
    thresholdBytes: raw?.thresholdBytes || CHUNK_DEFAULTS.thresholdBytes,
    maxCount: raw?.maxCount || CHUNK_DEFAULTS.maxCount,
    crc32: raw?.crc32 ?? CHUNK_DEFAULTS.crc32,
    total: raw?.total || 0,
    totalSize: raw?.totalSize || 0,
    chunkSize: raw?.chunkSize || 0,
    uploaded: raw?.uploaded ?? [],
    failed: raw?.failed ?? [],
    missing: raw?.missing ?? [],
  };
}

/** 总分片数（向上取整，至少 1） */
export function computeChunkCount(sizeBytes: number, chunkSize: number): number {
  const unit = Math.max(1, Math.floor(chunkSize) || CHUNK_DEFAULTS.sizeBytes);
  return Math.max(1, Math.ceil((Number(sizeBytes) || 0) / unit));
}

export interface ChunkedUploadParams {
  filePath: string;
  md5: string;
  size: number;
  originalName: string;
  plan: ChunkPlan;
  onProgress?: (p: { percent: number; done: number; total: number }) => void;
  /** 当前片任务句柄（供取消时 abort） */
  onChunkTask?: (task: UniApp.UploadTask) => void;
  isCanceled?: () => boolean;
  onEvent?: (name: string, payload?: Record<string, unknown>) => void;
}

// ==================== 文件系统封装 ====================

const RETRY_DELAYS = [1000, 2000];

function fsManager(): UniNamespace.FileSystemManager {
  return uni.getFileSystemManager();
}

function readChunk(filePath: string, position: number, length: number): Promise<ArrayBuffer> {
  return new Promise((resolve, reject) => {
    fsManager().readFile({
      filePath,
      position,
      length,
      success: (res: any) => resolve(res.data as ArrayBuffer),
      fail: (err: any) => reject(new Error(err?.errMsg || "读取分片失败")),
    });
  });
}

function writeTempFile(filePath: string, data: ArrayBuffer): Promise<void> {
  return new Promise((resolve, reject) => {
    fsManager().writeFile({
      filePath,
      data,
      success: () => resolve(),
      fail: (err: any) => reject(new Error(err?.errMsg || "写入临时分片失败")),
    });
  });
}

/** 删除临时分片文件：失败仅忽略（不阻断上传流程） */
function unlinkFile(filePath: string): Promise<void> {
  return new Promise((resolve) => {
    fsManager().unlink({
      filePath,
      success: () => resolve(),
      fail: () => resolve(),
    });
  });
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/** 待传分片：failed + missing，缺失时按 total 与 uploaded 自行推导 */
function resolvePending(plan: ChunkPlan, total: number): number[] {
  const done = new Set(plan.uploaded || []);
  const pending = new Set<number>([...(plan.failed || []), ...(plan.missing || [])]);
  if (!pending.size) {
    for (let i = 0; i < total; i += 1) {
      if (!done.has(i)) pending.add(i);
    }
  }
  return [...pending].filter((i) => !done.has(i) && i >= 0 && i < total).sort((a, b) => a - b);
}

// ==================== 主流程 ====================

/**
 * 分片上传视频，返回 file_id（与整体上传交付物一致）
 *
 * @throws 单片三次全败 / complete 失败（调用方可降级为整体上传）
 */
export async function uploadVideoChunked(params: ChunkedUploadParams): Promise<number> {
  const { filePath, md5, size, originalName, plan, onProgress, onChunkTask, isCanceled, onEvent } =
    params;

  const chunkSize = plan.sizeBytes || CHUNK_DEFAULTS.sizeBytes;
  const total = plan.total || computeChunkCount(size, chunkSize);
  const useCrc = plan.crc32 !== false;
  const tmpPath = `${wx.env.USER_DATA_PATH}/td_chunk.part`;

  const pending = resolvePending(plan, total);
  const skipped = Math.max(total - pending.length, 0);
  if (skipped > 0) {
    onEvent?.("video_chunk_resume", { skipped, pending: pending.length, total });
  }

  let done = skipped;
  const emit = (currentPercent = 0) => {
    const percent = Math.min(Math.round(((done + currentPercent / 100) / total) * 100), 100);
    onProgress?.({ percent, done, total });
  };

  let sessionSent = false;

  const uploadOne = async (index: number): Promise<void> => {
    const position = index * chunkSize;
    const length = Math.min(chunkSize, Math.max(size - position, 0));
    const buffer = await readChunk(filePath, position, length);

    let crc32 = "";
    if (useCrc) {
      try {
        crc32 = crc32Of(buffer);
      } catch {
        crc32 = ""; // 摘要失败退化为仅长度校验，不阻断上传
      }
    }

    await writeTempFile(tmpPath, buffer);
    const formData: Record<string, string> = {
      md5,
      index: String(index),
      length: String(length),
      ...(crc32 ? { crc32 } : {}),
    };
    if (!sessionSent) {
      // 首个待传片携带会话参数（服务端幂等建会话）
      formData.total = String(total);
      formData.size_bytes = String(size);
      formData.original_name = originalName;
    }

    try {
      await uploadRaw({
        path: "/upload/video/chunk",
        filePath: tmpPath,
        fieldName: "file",
        formData,
        timeout: resolveUploadTimeout(chunkSize),
        onTask: (task) => {
          onChunkTask?.(task);
          // 任务创建时已取消 → 立即中断，避免白耗流量
          if (isCanceled?.()) task.abort();
        },
        onProgress: (p) => emit(Number(p.percent) || 0),
      });
      sessionSent = true;
      onEvent?.("video_chunk_success", { index, size: length });
    } finally {
      await unlinkFile(tmpPath);
    }
  };

  const uploadWithRetry = async (index: number): Promise<void> => {
    let lastError: Error | null = null;
    for (let attempt = 0; attempt <= RETRY_DELAYS.length; attempt += 1) {
      if (isCanceled?.()) throw new Error("上传已取消");
      try {
        await uploadOne(index);
        return;
      } catch (err) {
        lastError = (err as Error) || new Error("分片上传失败");
        if (isCanceled?.()) throw lastError;
        if (attempt < RETRY_DELAYS.length) await delay(RETRY_DELAYS[attempt]);
      }
    }
    onEvent?.("video_chunk_failed", { index, error: lastError?.message || "" });
    throw lastError || new Error("分片上传失败");
  };

  emit(0);
  for (const index of pending) {
    if (isCanceled?.()) throw new Error("上传已取消");
    await uploadWithRetry(index);
    done += 1;
    emit(0);
  }

  try {
    const fileId = await completeChunkUpload(md5, size);
    onEvent?.("video_chunk_complete", { file_id: fileId, total });
    return fileId;
  } catch (err) {
    // 409（整文件 MD5 不符）：按服务端 missing 局部重传一次，仍失败则向上抛（降级整体上传）
    if (!(err instanceof ApiError) || err.status !== 409) throw err;
    onEvent?.("video_chunk_mismatch", { md5, total });
    const latest = await fetchChunkProgress(md5).catch(() => null);
    const retry = latest
      ? resolvePending(
          normalizeChunkPlan({
            uploaded: latest.ok,
            failed: latest.failed,
            missing: latest.missing,
            total: latest.total,
            sizeBytes: chunkSize,
          }),
          total,
        )
      : Array.from({ length: total }, (_, i) => i);
    for (const index of retry) {
      if (isCanceled?.()) throw new Error("上传已取消");
      await uploadWithRetry(index);
    }
    const fileId = await completeChunkUpload(md5, size);
    onEvent?.("video_chunk_complete", { file_id: fileId, total, retried: true });
    return fileId;
  }
}
