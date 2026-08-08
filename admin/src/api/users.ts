import request from './index'

export interface User {
  id: number
  openid: string
  nickname: string
  avatar_url: string
  gender: number | null
  birthday: string | null
  created_at: string
}

export interface UserListResponse {
  items: User[]
  total: number
}

export function getUsers(params: { offset?: number; limit?: number }): Promise<UserListResponse> {
  return request.get('/api/admin/users', { params })
}

export function getUser(userId: number): Promise<User> {
  return request.get(`/api/admin/users/${userId}`)
}

export function deleteUser(userId: number) {
  return request.delete(`/api/admin/users/${userId}`)
}
