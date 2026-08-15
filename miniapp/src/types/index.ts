/**
 * 小程序端数据模型类型定义
 *
 * 由原 Web 版 `docs/reference/tennis-diary/src/types.ts` 迁移而来，
 * 字段命名已对齐后台 B1 Pydantic Schemas（蛇形命名）。
 *
 * 说明：
 * - 主实体接口（Diary / Gear / WeightRecord / Analysis / Checkin / Post）
 *   对应后台 `*Response`，字段与接口响应一致。
 * - 创建/更新入参类型（*Create / *Update）供 Phase1-7 网络层与 Phase2 页面使用，
 *   继承后台 `*Create` / `*Update` 字段。
 * - Course / AISettings 为前端本地实体，后台无对应接口。
 * - RallyClip 的视频文件在小程序端用 `File`（`uni.chooseMedia` 返回）而非 Blob。
 */

// ==================== 通用 ====================

/** 通用 API 消息响应（DELETE 等操作返回） */
export interface MessageResponse {
  message: string
}

// ==================== 用户 / 认证 ====================

/** 当前登录用户（后台 UserResponse） */
export interface User {
  id: number
  openid: string
  nickname: string
  avatar_url: string
  gender: number // 0=保密 1=男 2=女
  birthday: string // YYYY-MM-DD
}

/** 登录请求（后台 LoginRequest） */
export interface LoginRequest {
  code: string // wx.login 返回的临时 code
}

/** 登录响应（后台 TokenResponse） */
export interface Token {
  access_token: string
  token_type: string
}

/** 登录响应（后台 LoginResponse） */
export interface LoginResponse extends Token {
  user: User
  is_new: boolean
}

/** 更新用户资料入参（后台 UserUpdate） */
export interface UserUpdate {
  nickname?: string
  avatar_url?: string
  gender?: number
  birthday?: string
}

// ==================== 日记 ====================

export type SessionType = "训练" | "比赛" | "发球机" | "发球练习"

/** 花费明细（后台 CostItem） */
export interface CostItem {
  name: string
  amount: number
}

/** 装备使用明细（后台 GearUse） */
export interface GearUse {
  name: string
  feeling: string
}

/** 日记 — 后台 DiaryResponse 字段 */
export interface Diary {
  id: number
  date: string // YYYY-MM-DD
  time: string // HH:mm
  type: SessionType
  duration: number // 分钟
  intensity: 1 | 2 | 3 | 4 | 5
  mood: 1 | 2 | 3 | 4 | 5
  costs: CostItem[]
  gears: GearUse[]
  notes: string
  created_at: number // 时间戳（秒）
}

/** 创建日记入参 — 后台 DiaryCreate */
export interface DiaryCreate {
  date: string
  time?: string
  type?: SessionType
  duration?: number
  intensity?: 1 | 2 | 3 | 4 | 5
  mood?: 1 | 2 | 3 | 4 | 5
  costs?: CostItem[]
  gears?: GearUse[]
  notes?: string
}

/** 更新日记入参 — 后台 DiaryUpdate（字段可选） */
export type DiaryUpdate = Partial<DiaryCreate>

// ==================== 装备 ====================

/** 装备 — 后台 GearResponse 字段 */
export interface Gear {
  id: number
  category: string
  name: string
  buy_date: string // YYYY-MM-DD
  price: number
  feeling: string
  photo: string // dataURL 或文件路径
  created_at: number // 时间戳（秒）
}

/** 创建装备入参 — 后台 GearCreate */
export interface GearCreate {
  category?: string
  name?: string
  buy_date?: string
  price?: number
  feeling?: string
  photo?: string
}

/** 更新装备入参 — 后台 GearUpdate */
export type GearUpdate = Partial<GearCreate>

// ==================== 体重 ====================

/** 体重记录 — 后台 WeightResponse 字段 */
export interface WeightRecord {
  id: number
  date: string // YYYY-MM-DD
  weight: number
  bust?: number
  waist?: number
  hip?: number
  created_at: number // 时间戳（秒）
}

/** 创建体重记录入参 — 后台 WeightCreate */
export interface WeightCreate {
  date: string
  weight: number
  bust?: number
  waist?: number
  hip?: number
}

// ==================== 动作分析 ====================

export type AnalysisKind = "综合" | "正手" | "反手" | "截击" | "发球" | "高压"

/** 分析维度得分（后台 DimensionScore） */
export interface DimensionScore {
  name: string
  score: number
  comment: string
}

/** 改进建议（后台 ImprovementItem） */
export interface ImprovementItem {
  issue: string
  advice: string
}

/** 分析报告（后台 AnalysisReportSchema） */
export interface AnalysisReport {
  score: number
  summary: string
  ntrp?: string // 参考 NTRP 等级，如 "3.0"
  dimensions: DimensionScore[]
  rhythm: string
  strengths: string[]
  improvements: ImprovementItem[]
}

/** 动作分析 — 后台 AnalysisResponse 字段 */
export interface Analysis {
  id: number
  date: string // YYYY-MM-DD
  kind: AnalysisKind
  mode: "single" | "full" // 单次挥拍 / 综合分析
  score: number
  summary: string
  ntrp?: string // 最近一次 AI 评估的参考 NTRP
  report?: AnalysisReport
  thumb?: string // 封面帧路径（姿态落库后为带骨架标注的封面）
  highlights?: string[] // 高光帧路径
  video_url?: string // 视频文件相对路径
  pose?: AnalysisPose // 姿态分析结果（Step 83）
  created_at: number // 时间戳（秒）
}

/** 创建分析入参 — 后台 AnalysisCreate */
export interface AnalysisCreate {
  date: string
  kind?: AnalysisKind
  mode?: "single" | "full"
  score?: number
  summary?: string
  ntrp?: string
  report?: AnalysisReport
  thumb?: string
  highlights?: string[]
  video_url?: string
  pose?: AnalysisPose
}

/** 视频上传结果 — 后台 POST /api/video/upload data */
export interface VideoUploadResult {
  frames: string[] // 抽帧 base64 dataURL（AI 分析用）
  frame_urls: string[] // 帧文件相对路径
  duration: number // 秒
  frame_rate?: number // 视频帧率（fps）
  thumbnail: string // 封面帧 base64 dataURL
  hit_time: number
  mode: "single" | "full"
  kind: string
  video_url: string // 视频文件相对路径
}

/** 姿态关键点（BlazePose 33 项之一） */
export interface PoseLandmark {
  x: number
  y: number
  z: number
  visibility: number
}

/** 姿态测量（肘/膝/躯干角，取可见度更高一侧） */
export interface PoseMetrics {
  elbowAngle: number
  kneeAngle: number
  trunkLean: number
}

/** 姿态分析结果 — 后台 POST /api/pose/analyze data */
export interface PoseResult {
  frames: { landmarks: PoseLandmark[] }[]
  metrics: PoseMetrics | null
  detected: boolean
  /** 骨架帧相对 URL（save_skeleton 时返回） */
  skeleton_frames?: string[]
  /** 骨架关键帧动画 mp4 相对 URL（ffmpeg 可用时返回） */
  skeleton_video_url?: string
  /** 封面骨架帧相对 URL */
  skeleton_thumb?: string
}

/** 已落库分析的姿态结果（后台 AnalysisResponse.pose） */
export interface AnalysisPose {
  detected: boolean
  metrics?: PoseMetrics
  skeleton_frames?: string[]
  skeleton_video_url?: string
  skeleton_thumb?: string
}

// ==================== 训练营打卡 ====================

/** 打卡记录 — 后台 CheckinResponse 字段 */
export interface Checkin {
  id: number
  course_id: string
  date: string // YYYY-MM-DD
  created_at: number // 时间戳（秒）
}

/** 创建打卡入参 — 后台 CheckinCreate */
export interface CheckinCreate {
  course_id: string
  date: string
}

/** 训练营课程（前端本地数据，后台无实体） */
export interface Course {
  id: string
  title: string
  kind: "热身" | "拉伸" | "跟练"
  duration: string
  url: string
  desc: string
}

// ==================== 社媒发布 ====================

export type PostPlatform = "小红书" | "朋友圈" | "其他"
export type PostStatus = "草稿" | "已发布"

/** 发布记录 — 后台 PostResponse 字段 */
export interface Post {
  id: number
  date: string // YYYY-MM-DD
  platform: PostPlatform
  title: string
  content: string
  status: PostStatus
  created_at: number // 时间戳（秒）
}

/** 创建发布入参 — 后台 PostCreate */
export interface PostCreate {
  date: string
  platform?: PostPlatform
  title?: string
  content?: string
  status?: PostStatus
}

// ==================== 挥拍片段（Phase 后期） ====================

/** 挥拍视频片段（前端本地数据，后台无实体） */
export interface RallyClip {
  id?: number
  date: string // YYYY-MM-DD
  name: string
  cover?: string // 封面路径
  video?: File // 小程序端用 uni.chooseMedia 获取的临时文件
  duration: number // 秒
  createdAt: number // 时间戳（秒）
}

// ==================== AI 设置（前端本地数据） ====================

export interface AISettings {
  apiKey: string
  baseUrl: string
  model: string
}

// ==================== 统计 ====================

/** 统计数据汇总 — 后台 StatsResponse */
export interface Stats {
  total_sessions: number
  total_duration: number // 分钟
  avg_intensity: number
  avg_mood: number
  total_cost: number
  total_gears: number
  total_analyses: number
  avg_score: number
}
