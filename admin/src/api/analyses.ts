import request from './index'

export interface DimensionScore {
  name: string
  score: number
  comment: string
}

export interface AnalysisReport {
  score: number
  summary: string
  ntrp?: string
  dimensions: DimensionScore[]
  rhythm: string
  strengths: string[]
  improvements: { issue: string; advice: string }[]
}

export interface AnalysisPose {
  detected: boolean
  metrics?: { elbowAngle: number; kneeAngle: number; trunkLean: number } | null
  skeleton_frames?: string[] | null
  skeleton_video_url?: string | null
  skeleton_thumb?: string | null
}

export interface Analysis {
  id: number
  user_id: number
  date: string
  kind: string
  mode: string
  score: number | null
  summary: string
  ntrp: string | null
  created_at: string
  report?: AnalysisReport | string | null
  thumb?: string | null
  highlights?: string[] | null
  video_url?: string | null
  pose?: AnalysisPose | null
  user?: {
    id: number
    nickname: string
  }
}

export interface AnalysisListResponse {
  items: Analysis[]
  total: number
}

export function getAnalyses(params: { offset?: number; limit?: number; user_id?: number }): Promise<AnalysisListResponse> {
  return request.get('/api/admin/analyses', { params })
}

export function getAnalysis(id: number): Promise<Analysis> {
  return request.get(`/api/admin/analyses/${id}`)
}

export function deleteAnalysis(id: number) {
  return request.delete(`/api/admin/analyses/${id}`)
}