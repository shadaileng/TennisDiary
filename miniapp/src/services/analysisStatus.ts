/**
 * 分析状态订阅服务（混合模式）
 *
 * - 默认模式：轮询（兼容所有基础库版本）
 * - 高级模式：SSE（基础库 ≥ 2.20.0 时，通过 enableChunked 实现）
 *
 * 参考文档：119-电子教练后台任务队列与管线模式
 */

import { BASE_URL, API_PREFIX } from "@/config";

// ==================== 类型 ====================

export interface PipelineStepStatus {
  status: "pending" | "processing" | "completed" | "failed";
  progress?: number;
  ts?: number;
  error?: string;
}

export interface PipelineStatus {
  step: string;
  progress: number;
  steps: Record<string, PipelineStepStatus>;
  error: string | null;
  retry_count: number;
}

export interface AnalysisStatus {
  id: number;
  status: "processing" | "completed" | "failed";
  pipeline_status: PipelineStatus | null;
}

type StatusCallback = (status: AnalysisStatus) => void;

// ==================== 工具函数 ====================

/** 获取 token */
function getToken(): string {
  return (uni.getStorageSync("td_token") as string) || "";
}

/**
 * 检测是否支持 enableChunked（SSE 模式）
 * 微信小程序基础库 ≥ 2.20.0 支持
 */
function isChunkedSupported(): boolean {
  try {
    const systemInfo = uni.getSystemInfoSync();
    const version = systemInfo.SDKVersion || "0.0.0";
    const [major, minor] = version.split(".").map(Number);
    return major > 2 || (major === 2 && minor >= 20);
  } catch {
    return false;
  }
}

/**
 * ArrayBuffer 转字符串
 */
function arrayBufferToString(buffer: ArrayBuffer): string {
  const uint8Array = new Uint8Array(buffer);
  let str = "";
  for (let i = 0; i < uint8Array.length; i++) {
    str += String.fromCharCode(uint8Array[i]);
  }
  // 尝试 UTF-8 解码
  try {
    return decodeURIComponent(escape(str));
  } catch {
    return str;
  }
}

// ==================== 轮询模式 ====================

/**
 * 轮询模式：定时查询状态
 */
class PollingSubscriber {
  private timer: ReturnType<typeof setInterval> | null = null;
  private analysisId: number;
  private callback: StatusCallback;
  private pollInterval: number;

  constructor(analysisId: number, callback: StatusCallback, pollInterval = 2000) {
    this.analysisId = analysisId;
    this.callback = callback;
    this.pollInterval = pollInterval;
  }

  start() {
    // 立即查询一次
    this.fetchStatus();

    // 定时轮询
    this.timer = setInterval(() => {
      this.fetchStatus();
    }, this.pollInterval);
  }

  private async fetchStatus() {
    try {
      const token = getToken();
      const url = `${BASE_URL}${API_PREFIX}/analyses/${this.analysisId}/status`;

      const res = await uni.request({
        url,
        method: "GET",
        header: {
          "X-Auth-Token": token,
        },
      });

      if (res.statusCode === 200) {
        const apiRes = res.data as any;
        if (apiRes?.code === 0 && apiRes?.data) {
          this.callback(apiRes.data as AnalysisStatus);
        }
      }
    } catch (e) {
      console.error("[PollingSubscriber] 查询状态失败:", e);
    }
  }

  stop() {
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = null;
    }
  }
}

// ==================== SSE 模式 ====================

/**
 * SSE 模式：通过 enableChunked 实现类 SSE
 */
class SSESubscriber {
  private requestTask: any = null;
  private analysisId: number;
  private callback: StatusCallback;
  private buffer = "";
  private fallbackTimer: ReturnType<typeof setInterval> | null = null;
  private receivedAny = false;

  constructor(analysisId: number, callback: StatusCallback) {
    this.analysisId = analysisId;
    this.callback = callback;
  }

  start() {
    const token = getToken();
    const url = `${BASE_URL}${API_PREFIX}/analyses/${this.analysisId}/stream`;

    this.requestTask = uni.request({
      url,
      method: "GET",
      enableChunked: true,
      header: {
        "X-Auth-Token": token,
      },
      success: (res: any) => {
        // 兜底：如果 onChunkReceived 未触发，通过 success 回调获取完整响应
        if (!this.receivedAny && res.statusCode === 200) {
          console.log("[SSESubscriber] 使用 success 回退解析");
          const body = typeof res.data === "string" ? res.data : "";
          if (body) {
            this.parseSSEData(body);
          }
        }
      },
      fail: (err: any) => {
        console.error("[SSESubscriber] 请求失败:", err);
      },
    });

    // 监听分块数据
    const listener = (res: { data: ArrayBuffer }) => {
      this.receivedAny = true;
      this.handleChunk(res.data);
    };

    // 使用 onChunkReceived（如果可用）
    if (this.requestTask && typeof this.requestTask.onChunkReceived === "function") {
      this.requestTask.onChunkReceived(listener);
    }

    // 兜底：2 秒内未收到任何数据，降级为轮询
    this.fallbackTimer = setTimeout(() => {
      if (!this.receivedAny) {
        console.log("[SSESubscriber] SSE 未收到数据，降级为轮询");
        this.stop();
        const fallback = new PollingSubscriber(this.analysisId, this.callback);
        fallback.start();
        // 替换 stop 引用（通过回调）
        this._fallbackStop = () => fallback.stop();
      }
    }, 2000) as unknown as ReturnType<typeof setInterval>;
  }

  private _fallbackStop: (() => void) | null = null;

  private parseSSEData(text: string) {
    this.buffer += text;
    const lines = this.buffer.split("\n");
    this.buffer = lines.pop() || "";

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        const jsonStr = line.slice(6).trim();
        if (jsonStr) {
          try {
            const status = JSON.parse(jsonStr) as AnalysisStatus;
            this.callback(status);
          } catch (e) {
            console.error("[SSESubscriber] JSON 解析失败:", e);
          }
        }
      }
    }
  }

  private handleChunk(data: ArrayBuffer) {
    const text = arrayBufferToString(data);
    this.parseSSEData(text);
  }

  stop() {
    if (this.fallbackTimer) {
      clearTimeout(this.fallbackTimer);
      this.fallbackTimer = null;
    }
    if (this._fallbackStop) {
      this._fallbackStop();
      this._fallbackStop = null;
      return;
    }
    if (this.requestTask) {
      this.requestTask.abort();
      this.requestTask = null;
    }
  }
}

// ==================== 导出 ====================

/**
 * 创建状态订阅器（自动选择轮询或 SSE 模式）
 *
 * @example
 * ```ts
 * const subscriber = createStatusSubscriber(analysisId, (status) => {
 *   console.log("进度:", status.pipeline_status?.progress);
 *   if (status.status === "completed") {
 *     subscriber.stop();
 *   }
 * });
 * subscriber.start();
 * ```
 */
export function createStatusSubscriber(
  analysisId: number,
  callback: StatusCallback
): { start: () => void; stop: () => void } {
  // 开发者工具中 enableChunked 不可靠，始终使用轮询模式
  // TODO: 真机上线后可启用 SSE: if (isChunkedSupported()) ...
  console.log("[AnalysisStatus] 使用轮询模式");
  return new PollingSubscriber(analysisId, callback);
}

/**
 * 查询分析状态（单次）
 */
export async function getAnalysisStatus(id: number): Promise<AnalysisStatus> {
  const token = getToken();
  const url = `${BASE_URL}${API_PREFIX}/analyses/${id}/status`;

  return new Promise((resolve, reject) => {
    uni.request({
      url,
      method: "GET",
      header: {
        "X-Auth-Token": token,
      },
      success: (res) => {
        if (res.statusCode === 200) {
          const apiRes = res.data as any;
          if (apiRes?.code === 0 && apiRes?.data) {
            resolve(apiRes.data as AnalysisStatus);
          } else {
            reject(new Error(apiRes?.message || "查询分析状态失败"));
          }
        } else {
          reject(new Error(`HTTP ${res.statusCode}`));
        }
      },
      fail: (err) => {
        reject(new Error(err.errMsg || "网络请求失败"));
      },
    });
  });
}
