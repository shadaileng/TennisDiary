/**
 * 浏览器原生请求（<img> / <video> / fetch / <a download>）的 URL 解析。
 *
 * Admin 前端与后端 API 跨域部署（admin 静态站点 ≠ backend 域名，且无同源反代），
 * axios 请求已由 api/index.ts 的 baseURL 统一处理；
 * 但原生请求不走 axios，相对路径会被浏览器解析到 Admin 自身域名 → 404。
 * 因此所有原生资源地址必须显式补齐后端域名。
 */

const API_BASE: string = (import.meta.env.VITE_API_BASE_URL as string | undefined) || ''

/** 绝对 URL 判定：http(s) 完整地址 或 base64 dataURL —— 一律原样返回 */
const isAbsolute = (p: string): boolean =>
  p.startsWith('http://') || p.startsWith('https://') || p.startsWith('data:')

/** 文件管理静态资源：相对路径 → {base}/api/admin/system/files/{rel_path} */
export function fileUrl(p?: string | null): string {
  if (!p) return ''
  if (isAbsolute(p)) return p
  return `${API_BASE}/api/admin/system/files/${p}`
}

/** 用户头像：avatars/ → avatar/，相对路径 → {base}/api/upload/{path} */
export function avatarUrl(p?: string | null): string {
  if (!p) return ''
  if (isAbsolute(p)) return p
  const path = p.replace(/^avatars\//, 'avatar/')
  return `${API_BASE}/api/upload/${path}`
}

/** 文件管理下载端点（与静态预览端点路径不同，需单独拼） */
export function fileDownloadUrl(fileId: number): string {
  return `${API_BASE}/api/admin/files/${fileId}/download`
}
