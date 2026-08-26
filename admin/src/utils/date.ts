const TZ = 'Asia/Shanghai'

/** Unix 秒级时间戳 → 完整日期时间（东八区） */
export function formatTs(ts: number | null | undefined): string {
  if (!ts) return '--'
  return new Date(ts * 1000).toLocaleString('zh-CN', { timeZone: TZ })
}

/** Unix 秒级时间戳 → 短日期时间（东八区）：8/25 10:50 */
export function formatTsShort(ts: number | null | undefined): string {
  if (!ts) return '--'
  const d = new Date(ts * 1000)
  const month = d.getMonth() + 1
  const day = d.getDate()
  const h = String(d.getHours()).padStart(2, '0')
  const m = String(d.getMinutes()).padStart(2, '0')
  return `${month}/${day} ${h}:${m}`
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
