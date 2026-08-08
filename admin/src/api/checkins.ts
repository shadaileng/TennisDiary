import request from './index'

export interface Checkin {
  id: number
  user_id: number
  course_id: string
  date: string
  created_at: string
  user?: {
    id: number
    nickname: string
  }
}

export interface CheckinListResponse {
  items: Checkin[]
  total: number
}

export function getCheckins(params: { offset?: number; limit?: number; user_id?: number }): Promise<CheckinListResponse> {
  return request.get('/api/admin/checkins', { params })
}

export function deleteCheckin(id: number) {
  return request.delete(`/api/admin/checkins/${id}`)
}
