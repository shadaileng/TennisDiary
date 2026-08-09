import request from './index'

export interface EventLog {
  id: number
  user_id: number | null
  level: 'info' | 'warn' | 'error' | 'fatal'
  type: 'network' | 'business' | 'crash' | 'custom'
  message: string
  stack: string
  page: string
  extra: Record<string, any>
  device_info: Record<string, any>
  client_time: number | null
  created_at: number
}

export interface EventLogListParams {
  level?: string
  type?: string
  user_id?: number
  keyword?: string
  trace_id?: string
  page?: number
  page_size?: number
}

export interface PaginatedEventLogs {
  items: EventLog[]
  total: number
  offset: number
  limit: number
}

export function getEventLogs(params: EventLogListParams): Promise<PaginatedEventLogs> {
  return request.get('/api/admin/events', { params })
}
