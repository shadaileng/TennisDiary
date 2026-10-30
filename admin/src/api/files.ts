import request from './index'
import { fileDownloadUrl } from '@/utils/fileUrl'

export interface AdminFile {
  id: number
  user_id: number
  md5: string
  original_name: string
  rel_path: string
  size_bytes: number
  mime_type: string
  upload_source: string
  ref_count: number
  business_type: string | null
  business_id: number | null
  created_at: number
  usage_status: string
  usage_reason: string
  /** 本体位置（147）：local=本地受管目录 / kodo=七牛对象存储 */
  storage: string
  /** 同步状态（147）：0=PENDING / 1=SYNCED / 2=FAILED */
  storage_status: number
}

export interface FileListResponse {
  items: AdminFile[]
  total: number
  offset: number
  limit: number
}

export interface FileStats {
  total_count: number
  total_size_bytes: number
  by_source: Record<string, { count: number; size_bytes: number }>
  marked_deleted_count?: number
  unreferenced_count?: number
}

export interface OrphanFileInfo {
  rel_path: string
  size_bytes: number
  modified_at: number
  inferred_user_id: number | null
  inferred_source: string
  usage_status: string
  usage_reason: string
}

export interface ScanResultResponse {
  total_files: number
  registered_files: number
  orphan_files: number
  orphans: OrphanFileInfo[]
  total_orphan_size: number
  status_counts?: Record<string, number>
}

export interface MigrateResult {
  dry_run: boolean
  scanned: number
  renamed: number
  already_named: number
  reused: number
  records_updated: number
  business_updated: number
  duplicates_merged: number
  conflicts: { from: string; to: string; md5: string }[]
  missing_files: string[]
}

export function migrateFilesToMd5(dryRun: boolean = true): Promise<MigrateResult> {
  return request.post('/api/admin/files/migrate-md5', null, { params: { dry_run: dryRun } })
}

export function getFiles(params: {
  offset?: number
  limit?: number
  user_id?: number
  upload_source?: string
  business_type?: string
  usage_status?: string
  storage_status?: number
}): Promise<FileListResponse> {
  return request.get('/api/admin/files', { params })
}

// ==================== S3 同步中心（147 §9.1） ====================

export type SyncScope = 'pending' | 'failed' | 'local' | 'selected'

export interface SyncStatus {
  total: number
  synced: number
  pending: number
  failed: number
  local_only: number
  running: boolean
  progress: { done: number; total: number; failed: number } | null
  last_sync_at: number | null
}

export interface SyncResult {
  dry_run: boolean
  scope: string
  queued: number
  skipped: number
  estimate_bytes: number
  task_id: string | null
}

export interface SingleSyncResult {
  file_id: number
  rel_path: string
  status: 'synced' | 'failed'
  storage: string
  storage_status: number
  task_id: string
}

export function getSyncStatus(): Promise<SyncStatus> {
  return request.get('/api/admin/files/sync-status')
}

export function startSync(body: {
  scope: SyncScope
  file_ids?: number[]
  dry_run?: boolean
  force?: boolean
}): Promise<SyncResult> {
  return request.post('/api/admin/files/sync', body)
}

export function syncFile(fileId: number): Promise<SingleSyncResult> {
  return request.post(`/api/admin/files/sync/${fileId}`)
}

export function getFileStats(): Promise<FileStats> {
  return request.get('/api/admin/files/stats/summary')
}

export function deleteFile(fileId: number) {
  return request.delete(`/api/admin/files/${fileId}`)
}

export function batchDeleteFiles(fileIds: number[]): Promise<{
  deleted: number
  skipped: number
  disk_removed: number
  errors: string[]
}> {
  return request.post('/api/admin/files/batch-delete', { file_ids: fileIds })
}

export function cleanupFiles(days: number = 30): Promise<{ cleaned: number }> {
  return request.post('/api/admin/files/cleanup', null, { params: { days } })
}

export function scanOrphanFiles(): Promise<ScanResultResponse> {
  return request.post('/api/admin/files/scan')
}

export function registerFiles(files: string[], defaultUserId: number = 0): Promise<{ registered: number }> {
  return request.post('/api/admin/files/register', { files, default_user_id: defaultUserId })
}

export function cleanupOrphanFiles(files: string[]): Promise<{ cleaned: number }> {
  return request.post('/api/admin/files/cleanup-orphans', { files })
}

export function getDownloadUrl(fileId: number): string {
  return fileDownloadUrl(fileId)
}

export interface RepairResultDetail {
  id: number
  rel_path: string
  action: string
  reason?: string
  old?: string
  new?: string
}

export interface RepairResult {
  scanned: number
  repaired: number
  unchanged: number
  skipped: number
  details: RepairResultDetail[]
}

export function repairFiles(onlyEmpty: boolean = true, uploadSource?: string): Promise<RepairResult> {
  return request.post('/api/admin/files/repair', {
    only_empty: onlyEmpty,
    upload_source: uploadSource ?? null,
  })
}
