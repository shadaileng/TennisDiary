/**
 * 分析状态订阅服务（轮询模式）
 *
 * 说明：历史版本曾设计 SSE（enableChunked）与轮询双模式，但微信开发者工具中
 * enableChunked 不可靠、真机也未真正启用，故已移除 SSE 实现（含此前死代码）。
 * 当前统一走轮询模式，逻辑更简单且各基础库版本均兼容。
 *
 * 参考文档：119-电子教练后台任务队列与管线模式
 */

import { API_PREFIX, BASE_URL } from "@/config";
import { STORAGE_KEYS } from "@/constants/storage";

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

/** 获取 token（统一从 STORAGE_KEYS 读取） */
function getToken(): string {
  return (uni.getStorageSync(STORAGE_KEYS.token) as string) || "";
}

// ==================== 步骤文案 ====================

/** 管线步骤 → 中文文案（analyze 与 report 共用，避免两处各写一份） */
const PIPELINE_STEP_LABELS: Record<string, string> = {
  init: "初始化…",
  upload: "处理视频…",
  ai: "AI评分中…",
  pose: "姿态分析中…",
  finalize: "保存结果…",
};

/** 步骤文案（未知步骤统一回退「分析中…」） */
export function stepLabel(step?: string | null): string {
  return (step && PIPELINE_STEP_LABELS[step]) || "分析中…";
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
    } catch {
      // 轮询失败静默忽略，下个周期重试；若接口本身报错由业务侧 logError 兜底
    }
  }

  stop() {
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = null;
    }
  }
}

// ==================== 导出 ====================

/**
 * 创建状态订阅器（轮询模式）
 *
 * @example
 * ```ts
 * const subscriber = createStatusSubscriber(analysisId, (status) => {
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
  return new PollingSubscriber(analysisId, callback);
}
