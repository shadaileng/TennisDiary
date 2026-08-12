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

export interface LogEntry {
  logs: string[]
  total: number
}

export type BackupType = 'manual' | 'pre_restore' | 'upload'

export interface Backup {
  name: string
  size: string
  created_at: string
  type?: BackupType
  status?: 'created' | 'restored' | 'deleted'
  note?: string
  restored_from_id?: number | null
  restored_from_name?: string | null
}

export interface BackupList {
  backups: Backup[]
  total: number
}

export function getSystemStats(): Promise<SystemStats> {
  return request.get('/api/admin/system/stats')
}

export function getHealthStatus(): Promise<HealthStatus> {
  return request.get('/api/admin/system/health')
}

export function getLogs(params: { level?: string; keyword?: string; limit?: number }): Promise<LogEntry> {
  return request.get('/api/admin/system/logs', { params })
}

export function createBackup(): Promise<{ message: string }> {
  return request.post('/api/admin/system/backup')
}

export function getBackups(): Promise<BackupList> {
  return request.get('/api/admin/system/backups')
}

export function restoreBackup(backupId: string): Promise<{ message: string }> {
  return request.post(`/api/admin/system/restore/${backupId}`)
}

export function deleteBackup(backupId: string): Promise<{ message: string }> {
  return request.delete(`/api/admin/system/backup/${backupId}`)
}

export function uploadBackup(file: File): Promise<{ message: string }> {
  const formData = new FormData()
  formData.append('file', file)
  return request.post('/api/admin/system/backup/upload', formData)
}
