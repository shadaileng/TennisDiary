import { del, get, post, put } from "./request";
import { uploadRaw } from "@/utils/upload";

import type {
  Analysis,
  AnalysisCreate,
  AnalysisReport,
  CaptionResult,
  Checkin,
  CheckinCreate,
  Diary,
  DiaryCreate,
  DiaryUpdate,
  Gear,
  GearCreate,
  GearUpdate,
  MessageResponse,
  PoseResult,
  Stats,
  VideoUploadResult,
  WeightCreate,
  WeightRecord,
} from "@/types";
import { createTraceId, logError, logInfo } from "@/utils/eventLogger";

/**
 * 业务数据 API 封装
 *
 * 统一对接 B1 后台 data 接口：
 * - /api/diaries   日记 CRUD
 * - /api/gears     装备 CRUD
 * - /api/weights   体重记录
 * - /api/checkin   训练营打卡
 * - /api/stats     统计数据汇总
 *
 * 路径省略 /api 前缀（request.ts 已统一拼接 API_PREFIX），
 * 类型与后台 *Response / *Create / *Update 对齐（见 types/index.ts）。
 */

// ==================== 日记 ====================

/** 当前用户日记列表（按日期倒序） */
export function getDiaries(): Promise<Diary[]> {
  return get<Diary[]>("/diaries");
}

/** 创建日记 */
export function createDiary(body: DiaryCreate): Promise<Diary> {
  return post<Diary>("/diaries", body);
}

/** 日记详情 */
export function getDiary(id: number): Promise<Diary> {
  return get<Diary>(`/diaries/${id}`);
}

/** 编辑日记（仅更新传入字段） */
export function updateDiary(id: number, body: DiaryUpdate): Promise<Diary> {
  return put<Diary>(`/diaries/${id}`, body);
}

/** 删除日记 */
export function deleteDiary(id: number): Promise<MessageResponse> {
  return del<MessageResponse>(`/diaries/${id}`);
}

// ==================== 装备 ====================

/** 当前用户装备列表 */
export function getGears(): Promise<Gear[]> {
  return get<Gear[]>("/gears");
}

/** 装备详情 */
export function getGear(id: number): Promise<Gear> {
  return get<Gear>(`/gears/${id}`);
}

/** 添加装备 */
export function createGear(body: GearCreate): Promise<Gear> {
  return post<Gear>("/gears", body);
}

/** 编辑装备（仅更新传入字段） */
export function updateGear(id: number, body: GearUpdate): Promise<Gear> {
  return put<Gear>(`/gears/${id}`, body);
}

/** 删除装备 */
export function deleteGear(id: number): Promise<MessageResponse> {
  return del<MessageResponse>(`/gears/${id}`);
}

// ==================== 体重 ====================

/** 当前用户体重记录列表 */
export function getWeights(): Promise<WeightRecord[]> {
  return get<WeightRecord[]>("/weights");
}

/** 添加体重记录 */
export function createWeight(body: WeightCreate): Promise<WeightRecord> {
  return post<WeightRecord>("/weights", body);
}

/** 删除体重记录 */
export function deleteWeight(id: number): Promise<MessageResponse> {
  return del<MessageResponse>(`/weights/${id}`);
}

// ==================== 打卡 ====================

/** 当前用户打卡记录列表 */
export function getCheckins(): Promise<Checkin[]> {
  return get<Checkin[]>("/checkin");
}

/** 签到（同用户+同课程+同日期幂等） */
export function createCheckin(body: CheckinCreate): Promise<Checkin> {
  return post<Checkin>("/checkin", body);
}

// ==================== 统计 ====================

/** 统计数据汇总 */
export function getStats(): Promise<Stats> {
  return get<Stats>("/stats");
}

// ==================== 电子教练（视频/AI/姿态/分析） ====================

/** 上传视频并抽帧（uploadRaw 直传后端，75-2 抽帧 + Step99 裁剪拼接） */
export function uploadVideo(
  filePath: string,
  formData: { mode: string; kind: string; hit_time?: string; cuts?: string },
): Promise<VideoUploadResult> {
  const traceId = createTraceId();
  return uploadRaw<VideoUploadResult>({
    path: "/video/upload",
    filePath,
    formData: { ...formData },
    timeout: 120000,
    onSuccess: (result, durationMs) => {
      logInfo(
        "视频上传成功",
        { video_url: result.video_url, mirage: result.mirage, duration_ms: durationMs },
        "business",
        "video_upload_success",
        traceId,
      );
    },
    onMirage: (result, durationMs) => {
      logInfo(
        "视频秒传",
        { video_url: result.video_url, duration_ms: durationMs },
        "business",
        "video_upload_mirage",
        traceId,
      );
    },
    onFailed: (error, durationMs) => {
      logError(
        "视频上传失败",
        { error: error.message, filePath, mode: formData.mode, kind: formData.kind, hit_time: formData.hit_time, cuts: formData.cuts, duration_ms: durationMs },
        undefined,
        "video_upload_failed",
        undefined,
        traceId,
      );
    },
  }) as Promise<VideoUploadResult>;
}

/** AI 六维评分（120s 超时，Key 存服务端，失败后端降级） */
export function analyzeSwing(
  frameUrls: string[],
  kind: string,
  mode: "single" | "full",
): Promise<AnalysisReport> {
  return post<AnalysisReport>("/ai/analyze", { frame_urls: frameUrls, kind, mode }, { timeout: 120000 });
}

/** AI 分享文案润色（30s 超时，Key 存服务端，失败后端降级为本地模板文案） */
export function generateCaption(template: string, style: string, text: string): Promise<CaptionResult> {
  return post<CaptionResult>("/ai/caption", { template, style, text }, { timeout: 30000 });
}

/** 姿态推理（33 关键点 + 角度测量 + 可选骨架落盘，60s 超时） */
export function analyzePose(
  frameUrls: string[],
  options?: {
    videoUrl?: string
    saveSkeleton?: boolean
    duration?: number
    frameRate?: number
    fullFrames?: boolean  // 是否逐帧生成骨架视频（null=自动判断）
  },
): Promise<PoseResult> {
  return post<PoseResult>(
    "/pose/analyze",
    {
      frame_urls: frameUrls,
      video_url: options?.videoUrl,
      save_skeleton: options?.saveSkeleton ?? false,
      duration: options?.duration,
      frame_rate: options?.frameRate,
      full_frames: options?.fullFrames,
    },
    { timeout: 60000 },
  );
}

/** 落库分析报告（AI 分析成功后调用，供历史回看） */
export function createAnalysis(body: AnalysisCreate): Promise<Analysis> {
  return post<Analysis>("/analyses", body);
}

/** 当前用户历史分析报告列表 */
export function getAnalyses(): Promise<{ items: Analysis[]; total: number }> {
  return get<{ items: Analysis[]; total: number }>("/analyses");
}

/** 分析报告详情 */
export function getAnalysis(id: number): Promise<Analysis> {
  return get<Analysis>(`/analyses/${id}`);
}

/** 删除分析报告 */
export function deleteAnalysis(id: number): Promise<MessageResponse> {
  return del<MessageResponse>(`/analyses/${id}`);
}
