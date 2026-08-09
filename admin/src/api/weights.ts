import request from './index'

export interface Weight {
  id: number
  user_id: number
  date: string
  weight: number
  bust: number | null
  waist: number | null
  hip: number | null
  created_at: number
  user?: {
    id: number
    nickname: string
  }
}

export interface WeightListResponse {
  items: Weight[]
  total: number
}

export function getWeights(params: { offset?: number; limit?: number; user_id?: number }): Promise<WeightListResponse> {
  return request.get('/api/admin/weights', { params })
}

export function deleteWeight(id: number) {
  return request.delete(`/api/admin/weights/${id}`)
}
