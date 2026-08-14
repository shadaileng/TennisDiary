import request from './index'

export type ConfigValueType = 'str' | 'secret' | 'url' | 'bool' | 'int' | 'select'
export type ConfigSource = 'db' | 'env' | 'builtin'

export interface ConfigItem {
  key: string
  category: string
  label: string
  description: string
  value_type: ConfigValueType
  editable: boolean
  value: string
  has_value: boolean
  default_value: string
  source: ConfigSource
  options: string[] | null
  updated_at: string | null
  updated_by: number | null
}

export interface ConfigCategory {
  key: string
  label: string
  description: string
  item_count: number
  editable_count: number
}

export interface ConfigSummary {
  total: number
  editable: number
  overridden: number
  categories: (ConfigCategory & { overridden: number })[]
}

export interface ConfigList {
  summary: ConfigSummary
  items: ConfigItem[]
}

export function getConfigs(): Promise<ConfigList> {
  return request.get('/api/admin/config')
}

export function updateConfig(key: string, value: string): Promise<ConfigItem> {
  return request.put(`/api/admin/config/${encodeURIComponent(key)}`, { value })
}

export function resetConfig(key: string): Promise<ConfigItem> {
  return request.delete(`/api/admin/config/${encodeURIComponent(key)}`)
}

export function resetAllConfigs(): Promise<{ message: string }> {
  return request.post('/api/admin/config/reset')
}

// ==================== AI 服务商 ====================

export interface AiProvider {
  id: number
  name: string
  base_url: string
  api_key: string
  models: string[]
  default_model: string
  enabled: boolean
  sort_order: number
  is_selected: boolean
  updated_at: string | null
}

export interface AiProviderList {
  providers: AiProvider[]
}

export interface AiProviderPayload {
  name: string
  base_url: string
  api_key: string
  models: string[]
  enabled: boolean
  sort_order?: number
}

export function getProviders(): Promise<AiProviderList> {
  return request.get('/api/admin/config/providers')
}

export function addProvider(payload: AiProviderPayload): Promise<AiProvider> {
  return request.post('/api/admin/config/providers', payload)
}

export function updateProvider(id: number, payload: AiProviderPayload): Promise<AiProvider> {
  return request.put(`/api/admin/config/providers/${id}`, payload)
}

export function deleteProvider(id: number): Promise<{ message: string }> {
  return request.delete(`/api/admin/config/providers/${id}`)
}
