/// <reference types="vite/client" />

declare module '*.vue' {
  import { DefineComponent } from 'vue'
  // eslint-disable-next-line @typescript-eslint/no-explicit-any, @typescript-eslint/ban-types
  const component: DefineComponent<{}, {}, any>
  export default component
}

interface ImportMetaEnv {
  /** 后台 API base URL */
  readonly VITE_API_BASE_URL: string
  /** 请求超时（毫秒） */
  readonly VITE_REQUEST_TIMEOUT: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

// 微信小程序 wx API 类型声明
declare const wx: {
  /** 监听小程序错误事件（渲染层错误） */
  onError(callback: (errMsg: string) => void): void
  getPrivacySetting(): Promise<{ needAuthorization: boolean; privacyContractName: string }>
  requirePrivacyAuthorize(): Promise<void>
  onNeedPrivacyAuthorization(resolve: (options: { buttonId?: string; event: 'agree' | 'disagree' | 'exposureAuthorization' }) => void, eventInfo: { referrer: string }): void
}
