import request from './index'

export interface LoginRequest {
  username: string
  password: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
}

export interface AdminInfo {
  id: number
  username: string
  nickname: string
  role: {
    id: number
    name: string
    code: string
    permissions: string[]
  }
}

export function login(data: LoginRequest): Promise<LoginResponse> {
  return request.post('/api/admin/auth/login', data)
}

export function getAdminInfo(): Promise<AdminInfo> {
  return request.get('/api/admin/auth/me')
}

export function updatePassword(data: { old_password: string; new_password: string }) {
  return request.put('/api/admin/auth/password', data)
}
