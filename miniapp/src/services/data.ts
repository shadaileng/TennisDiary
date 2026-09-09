import { del, get, post, put } from "./request";

import type {
  Analysis,
  AnalysisCreate,
  AnalysisStartRequest,
  AnalysisStartResult,
  CaptionResult,
  Diary,
  DiaryCreate,
  DiaryUpdate,
  Gear,
  GearCreate,
  GearUpdate,
  MessageResponse,
  Stats,
  WeightCreate,
  WeightRecord,
} from "@/types";

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

// ==================== 统计 ====================

/** 统计数据汇总 */
export function getStats(): Promise<Stats> {
  return get<Stats>("/stats");
}

// ==================== 电子教练（视频/AI/姿态/分析） ====================

/** AI 分享文案润色（30s 超时，Key 存服务端，失败后端降级为本地模板文案） */
export function generateCaption(template: string, style: string, text: string): Promise<CaptionResult> {
  return post<CaptionResult>("/ai/caption", { template, style, text }, { timeout: 30000 });
}

/** 落库分析报告（AI 分析成功后调用，供历史回看；118 后仍保留兼容旧链路） */
export function createAnalysis(body: AnalysisCreate): Promise<Analysis> {
  return post<Analysis>("/analyses", body);
}

/**
 * 启动分析（137：JSON 入参，凭 file_id 消费已上传视频）
 *
 * file_id 来自 /upload/check（秒传命中）或 /upload/video（实际上传），
 * 命中与未命中后续流程完全一致。
 */
export function startAnalysis(body: AnalysisStartRequest): Promise<AnalysisStartResult> {
  return post<AnalysisStartResult>("/analyses/start", body);
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

// ==================== 视频分片上传（140） ====================

/**
 * 分片上传完成：服务端段齐全校验 → 整文件 MD5 → 登记为受管文件
 *
 * @throws ApiError 409 表示整文件校验不符（调用方可查询进度后局部重传）
 */
export async function completeChunkUpload(md5: string, sizeBytes: number): Promise<number> {
  const res = await post<{ file_id?: number }>("/upload/video/complete", {
    md5,
    size_bytes: sizeBytes,
  });
  const fileId = Number(res?.file_id) || 0;
  if (!fileId) throw new Error("视频上传失败，请重试");
  return fileId;
}

/** 查询分片会话进度（断点续传 / 409 后确定重传范围） */
export function fetchChunkProgress(
  md5: string,
): Promise<{ ok: number[]; failed: number[]; missing: number[]; total: number; chunk_size: number }> {
  return get<{ ok: number[]; failed: number[]; missing: number[]; total: number; chunk_size: number }>(
    `/upload/video/chunks?md5=${encodeURIComponent(md5)}`,
  );
}
