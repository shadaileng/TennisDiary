const TZ = 'Asia/Shanghai'

/** Unix 秒级时间戳 → 完整日期时间（东八区） */
export function formatTs(ts: number | null | undefined): string {
  if (!ts) return '--'
  return new Date(ts * 1000).toLocaleString('zh-CN', { timeZone: TZ })
}

/** ISO 字符串 → 完整日期时间（东八区） */
export function formatIso(iso: string | null | undefined): string {
  if (!iso) return '--'
  return new Date(iso).toLocaleString('zh-CN', { timeZone: TZ })
}

/** ISO 字符串 → 仅日期（东八区） */
export function formatDate(iso: string | null | undefined): string {
  if (!iso) return '--'
  return new Date(iso).toLocaleDateString('zh-CN', { timeZone: TZ })
}
