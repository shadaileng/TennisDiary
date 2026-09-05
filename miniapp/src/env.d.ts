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

  // ===== 隐私接口（微信均为回调式，勿按 Promise 使用）=====
  /**
   * 查询当前隐私授权状态
   * 回调式：wx.getPrivacySetting({ success, fail })
   */
  getPrivacySetting(options: {
    success: (res: { needAuthorization: boolean; privacyContractName: string }) => void
    fail?: (err: any) => void
    complete?: () => void
  }): void

  /**
   * 以编程方式触发隐私授权弹窗
   * 需在用户点击等手势回调内调用，否则可能被微信限制
   * 回调式：wx.requirePrivacyAuthorize({ success, fail, complete })
   */
  requirePrivacyAuthorize(options?: {
    success: () => void
    fail?: (err: any) => void
    complete?: () => void
  }): void

  /** 打开隐私协议全文（官方用户隐私保护指引） */
  openPrivacyContract(options?: {
    fail?: (err: any) => void
    complete?: () => void
  }): void

  onNeedPrivacyAuthorization(resolve: (options: { buttonId?: string; event: 'agree' | 'disagree' | 'exposureAuthorization' }) => void, eventInfo: { referrer: string }): void

  /** 运行时环境变量（微信小程序全局） */
  env: {
    USER_DATA_PATH: string
  }
}
