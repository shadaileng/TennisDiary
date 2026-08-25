import request from './index'

export interface DerivedFileInfo {
  id: number
  rel_path: string
  upload_source: string
  business_type: string | null
  business_id: number | null
  size_bytes: number
  mime_type: string
}

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
  derived_files: DerivedFileInfo[]
  usage_status: string
  usage_reason: string
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
}

export function getFiles(params: {
  offset?: number
  limit?: number
  user_id?: number
  upload_source?: string
  business_type?: string
}): Promise<FileListResponse> {
  return request.get('/api/admin/files', { params })
}

export function getFile(fileId: number): Promise<AdminFile> {
  return request.get(`/api/admin/files/${fileId}`)
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

export function registerAllFiles(defaultUserId: number = 0): Promise<{ registered: number }> {
  return request.post('/api/admin/files/register-all', null, { params: { default_user_id: defaultUserId } })
}

export function cleanupOrphanFiles(files: string[]): Promise<{ cleaned: number }> {
  return request.post('/api/admin/files/cleanup-orphans', { files })
}
