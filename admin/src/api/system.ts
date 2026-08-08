import request from './index'

export interface SystemStats {
  stats: {
    users: number
    diaries: number
    gears: number
    weights: number
    checkins: number
    analyses: number
    posts: number
  }
  database_size: string
}

export interface HealthStatus {
  status: string
  version: string
  database: string
  disk_usage: string
  uptime: string
}

export function getSystemStats(): Promise<SystemStats> {
  return request.get('/api/admin/system/stats')
}

export function getHealthStatus(): Promise<HealthStatus> {
  return request.get('/api/admin/system/health')
}
