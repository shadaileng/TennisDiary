import request from './index'

export interface Analysis {
  id: number
  user_id: number
  date: string
  kind: string
  score: number | null
  summary: string
  ntrp: string | null
  created_at: string
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
