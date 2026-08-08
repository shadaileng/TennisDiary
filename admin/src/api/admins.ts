import request from './index'

export interface Admin {
  id: number
  username: string
  nickname: string
  role_id: number
  role?: {
    id: number
    name: string
    code: string
  }
  is_active: boolean
  last_login: string | null
  created_at: string
}

export interface AdminListResponse {
  items: Admin[]
  total: number
}

export function getAdmins(params: { offset?: number; limit?: number }): Promise<AdminListResponse> {
  return request.get('/api/admin/admins', { params })
}

export function createAdmin(data: { username: string; password: string; nickname: string; role_id: number }): Promise<Admin> {
  return request.post('/api/admin/admins', data)
}

export function updateAdmin(id: number, data: Partial<Admin>): Promise<Admin> {
  return request.put(`/api/admin/admins/${id}`, data)
}

export function deleteAdmin(id: number) {
  return request.delete(`/api/admin/admins/${id}`)
}

export function resetPassword(id: number, newPassword: string) {
  return request.put(`/api/admin/admins/${id}/password`, { new_password: newPassword })
}

export function toggleAdminStatus(id: number, isActive: boolean) {
  return request.put(`/api/admin/admins/${id}/status`, { is_active: isActive })
}
