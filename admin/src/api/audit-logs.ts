import request from './index'

export interface AuditLog {
  id: number
  source: string
  admin_id: number | null
  admin_username: string | null
  user_id: number | null
  user_nickname: string | null
  action: string
  resource_type: string
  resource_id: string | null
  description: string
  request_body: string | null
  request_path: string
  request_method: string
  response_code: number
  response_success: boolean
  response_message: string
  duration_ms: number
  ip_address: string
  user_agent: string
  created_at: string
}

export interface AuditLogList {
  items: AuditLog[]
  total: number
  offset: number
  limit: number
}

export function getAuditLogs(params: {
  source?: string
  admin_id?: number
  user_id?: number
  action?: string
  resource_type?: string
  start_date?: string
  end_date?: string
  offset?: number
  limit?: number
}): Promise<AuditLogList> {
  return request.get('/api/admin/audit-logs', { params })
}
