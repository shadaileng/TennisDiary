import request from './index'

export interface Gear {
  id: number
  user_id: number
  name: string
  category: string
  buy_date: string
  price: number
  feeling: string
  photo: string
  created_at: number
  user?: {
    id: number
    nickname: string
  }
}

export interface GearListResponse {
  items: Gear[]
  total: number
}

export function getGears(params: { offset?: number; limit?: number; user_id?: number }): Promise<GearListResponse> {
  return request.get('/api/admin/gears', { params })
}

export function getGear(id: number): Promise<Gear> {
  return request.get(`/api/admin/gears/${id}`)
}

export function deleteGear(id: number) {
  return request.delete(`/api/admin/gears/${id}`)
}
