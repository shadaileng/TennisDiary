import request from './index'

export interface Diary {
  id: number
  user_id: number
  date: string
  time: string
  type: string
  duration: number
  intensity: number
  mood: number
  costs: string
  gears: string
  notes: string
  created_at: string
  user?: {
    id: number
    nickname: string
  }
}

export interface DiaryListResponse {
  items: Diary[]
  total: number
}

export function getDiaries(params: { offset?: number; limit?: number; user_id?: number }): Promise<DiaryListResponse> {
  return request.get('/api/admin/diaries', { params })
}

export function getDiary(id: number): Promise<Diary> {
  return request.get(`/api/admin/diaries/${id}`)
}

export function deleteDiary(id: number) {
  return request.delete(`/api/admin/diaries/${id}`)
}
