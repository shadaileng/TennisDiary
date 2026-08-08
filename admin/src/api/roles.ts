import request from './index'

export interface Role {
  id: number
  name: string
  code: string
  description: string
  permissions: string[]
  is_system: boolean
}

export interface RoleListResponse {
  items: Role[]
  total: number
}

export interface Permission {
  code: string
  name: string
}

export interface PermissionListResponse {
  permissions: Record<string, string>
}

export function getRoles(): Promise<RoleListResponse> {
  return request.get('/api/admin/roles')
}

export function createRole(data: { name: string; code: string; description: string; permissions: string[] }): Promise<Role> {
  return request.post('/api/admin/roles', data)
}

export function updateRole(id: number, data: Partial<Role>): Promise<Role> {
  return request.put(`/api/admin/roles/${id}`, data)
}

export function deleteRole(id: number) {
  return request.delete(`/api/admin/roles/${id}`)
}

export async function getPermissions(): Promise<Permission[]> {
  const res: PermissionListResponse = await request.get('/api/admin/roles/permissions')
  return Object.entries(res.permissions).map(([code, name]) => ({ code, name: name as string }))
}
