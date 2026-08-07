import { del, get, post, put } from "./request";

import type {
  Checkin,
  CheckinCreate,
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
