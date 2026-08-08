/** 统一API响应格式 */
export interface ApiResponse<T = any> {
  code: number
  message: string
  success: boolean
  data: T | null
}

/** 分页数据 */
export interface PaginatedData<T> {
  items: T[]
  total: number
  offset: number
  limit: number
}
