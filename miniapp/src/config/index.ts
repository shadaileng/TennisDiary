/**
 * 全局配置
 */

declare const process: {
  env: { UNI_PLATFORM: string }
};

/** 是否为微信小程序端 */
const isMpWeixin = process.env.UNI_PLATFORM === "mp-weixin";

/**
 * 后台 API base URL
 *
 * 优先取 .env 中的 VITE_API_BASE_URL（由 import.meta.env 注入），
 * 未配置时按平台兜底：
 * - H5 端：`uni.request` 可直接访问 `localhost`
 * - 小程序端（微信开发者工具）：`127.0.0.1` 指向开发机，需在工具中勾选
 *   「不校验合法域名」；真机预览请改为局域网 IP。
 * - 生产环境：必须在 .env.production 中替换为已备案的 HTTPS 域名。
 */
export const BASE_URL: string =
  import.meta.env.VITE_API_BASE_URL ||
  (isMpWeixin ? "http://127.0.0.1:8000" : "http://localhost:8000");

/** 请求超时（毫秒），优先取 .env 的 VITE_REQUEST_TIMEOUT，默认 10000 */
export const REQUEST_TIMEOUT: number =
  Number(import.meta.env.VITE_REQUEST_TIMEOUT) || 10000;

/** API 接口前缀 */
export const API_PREFIX = "/api";
