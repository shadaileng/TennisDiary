/**
 * 媒体源解析（Step 141 离线占位）
 *
 * 统一把「封面 / 视频 / 骨架帧」等媒体 URL 解析为可渲染源：
 * - dataURL / 本地路径（/ 开头，含 wxfile:// 等临时路径）→ 原样返回（离线可用）
 * - 远程 URL（http / 相对路径）→ 在线时 `resolveUploadUrl` 拼成可访问地址；离线时返回本地占位图
 *
 * 配合 `<image @error>` 兜底（防 URL 失效 / 鉴权 401 导致破图）。
 */

import { resolveUploadUrl } from "@/utils";

/** 离线 / 加载失败时的本地占位图（随包静态资源，不依赖网络） */
export const OFFLINE_MEDIA_PLACEHOLDER = "/static/offline-media.png";

/** 是否为本地可直接渲染的源（dataURL 或本地路径） */
function isLocalSrc(url: string): boolean {
  if (!url) return false;
  if (url.startsWith("data:")) return true;
  // 本地路径（/ 开头：static、wxfile:// 等临时文件）原样可用
  if (url.startsWith("/")) return true;
  // 其余（http 远程链接、相对路径）视为需网络的远程资源
  return false;
}

/**
 * 解析媒体源。
 * @param url 原始媒体地址（可能为 dataURL / 相对路径 / http 完整地址 / 空）
 * @param online 当前网络是否可用
 */
export function resolveMediaSrc(url: string, online: boolean): string {
  if (!url) return OFFLINE_MEDIA_PLACEHOLDER;
  // 本地源无论在线离线都直接可用
  if (isLocalSrc(url)) return url;
  // 远程源：在线解析为可访问地址，离线返回占位
  return online ? resolveUploadUrl(url) : OFFLINE_MEDIA_PLACEHOLDER;
}
