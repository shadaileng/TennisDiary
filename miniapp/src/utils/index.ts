/**
 * 前端通用工具函数
 *
 * 由原 Web 版 `docs/reference/tennis-diary/src/utils.ts` 迁移而来，
 * 仅保留纯前端通用工具（枚举、日期/金额格式化、聚合）。
 * Web 专属（DOM / Blob / Canvas 截图等）留待 Phase 5 / B2。
 */

import { API_PREFIX, BASE_URL } from "@/config";
import { STORAGE_KEYS } from "@/constants/storage";
import { uploadFile, uploadRaw } from "@/utils/upload";

import type { CostItem } from "@/types";

// ==================== 枚举常量 ====================

/** 强度 1-5 的 label + emoji */
export const INTENSITY = [
  { v: 1, label: "很轻", emoji: "🌱" },
  { v: 2, label: "轻松", emoji: "😊" },
  { v: 3, label: "适中", emoji: "💪" },
  { v: 4, label: "较累", emoji: "🥵" },
  { v: 5, label: "极限", emoji: "🔥" },
] as const;

/** 心情 1-5 的 label + emoji */
export const MOOD = [
  { v: 1, label: "糟糕", emoji: "😫" },
  { v: 2, label: "不太好", emoji: "😕" },
  { v: 3, label: "一般", emoji: "😐" },
  { v: 4, label: "不错", emoji: "😄" },
  { v: 5, label: "很棒", emoji: "🤩" },
] as const;

/** 训练/比赛类型 */
export const SESSION_TYPES = ["训练", "比赛", "发球机", "发球练习"] as const;
/** 装备分类 */
export const GEAR_CATEGORIES = ["球拍", "球鞋", "衣服", "袜子", "帽子", "毛巾", "网球", "其他"] as const;
/** 动作分析种类 */
export const ANALYSIS_KINDS = ["综合", "正手", "反手", "截击", "发球", "高压"] as const;
/** 费用明细快捷标签默认种子（首装/候选池为空时兜底，保证首用即有快捷项；后续由真实填写项按频次挤出） */
export const DEFAULT_COST_PRESETS = ["场地费", "教练费", "网球", "饮料", "手胶", "穿线"] as const;

// ==================== 日期 / 时间 ====================

/** 两位数补零 */
export function pad(n: number): string {
  return n < 10 ? `0${n}` : `${n}`;
}

/** 今天的日期字符串 YYYY-MM-DD */
export function todayStr(): string {
  const d = new Date();
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

/** 当前时间字符串 HH:mm */
export function nowTimeStr(): string {
  const d = new Date();
  return `${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

/** 最近 n 天的日期数组（含今天，升序） */
export function lastNDays(n: number): string[] {
  const out: string[] = [];
  const d = new Date();
  for (let i = n - 1; i >= 0; i--) {
    const t = new Date(d);
    t.setDate(d.getDate() - i);
    out.push(`${t.getFullYear()}-${pad(t.getMonth() + 1)}-${pad(t.getDate())}`);
  }
  return out;
}

/** 日期所在星期几，如「周三」 */
export function weekdayCN(dateStr: string): string {
  const wd = ["日", "一", "二", "三", "四", "五", "六"];
  return `周${wd[new Date(dateStr + "T00:00:00").getDay()]}`;
}

/** 日期字符串的月份键 YYYY-MM */
export function monthKey(dateStr: string): string {
  return dateStr.slice(0, 7);
}

// ==================== 格式化 ====================

/** 时长格式化：90 → "1小时30分" */
export function fmtDuration(min: number): string {
  if (min < 60) return `${min}分钟`;
  const h = Math.floor(min / 60);
  const m = min % 60;
  return m ? `${h}小时${m}分` : `${h}小时`;
}

/** 金额格式化：整数 ¥8，小数保留两位 */
export function fmtMoney(n: number): string {
  return n % 1 === 0 ? `¥${n}` : `¥${n.toFixed(2)}`;
}

// ==================== 聚合 ====================

/** 花费明细合计 */
export function sumCosts(costs: CostItem[]): number {
  return costs.reduce((s, c) => s + (Number(c.amount) || 0), 0);
}

// ==================== 脱敏 ====================

/** 中间脱敏：数字/字符串太长时保留首尾各 keep 位，中间用 ***。过短则整体 *** */
export function maskMiddle(value: string | number, keep = 4): string {
  const s = String(value);
  if (s.length <= keep * 2) return "***";
  return `${s.slice(0, keep)}***${s.slice(-keep)}`;
}

/**
 * 将后端返回的上传文件相对 url 转为可展示的完整 URL。
 * - 头像 `avatars/<user_id>/<uuid>.<ext>` → `/api/upload/avatar/<user_id>/<uuid>.<ext>`
 * - 装备图片 / 视频/帧/骨架（`gears/`、`videos/` 开头的相对路径）
 *   → `/api/media/<url>?token=`（小程序 <image>/<video> 无法携带自定义头，
 *   媒体组件需 query 传 token，故装备图与视频统一走 media 端点）
 * - 绝对地址（http/data）原样返回
 */
export function resolveUploadUrl(url: string): string {
  if (!url) return "";
  if (/^https?:\/\//.test(url) || url.startsWith("data:")) return url;
  const parts = url.split("/");
  if (parts[0] === "avatars" && parts[1] && parts.length >= 3) {
    return `${BASE_URL}${API_PREFIX}/upload/avatar/${parts[1]}/${parts.slice(2).join("/")}`;
  }
  if ((parts[0] === "gears" || parts[0] === "videos") && parts[1] && parts.length >= 3) {
    const token = (uni.getStorageSync(STORAGE_KEYS.token) as string) || "";
    const sep = token ? `?token=${encodeURIComponent(token)}` : "";
    return `${BASE_URL}${API_PREFIX}/media/${url}${sep}`;
  }
  return url;
}

// ==================== 图片 ====================

/**
 * 上传装备封面图片到服务器，返回相对路径。
 * 内部使用 uploadFile 统一上传工具，事件钩子由调用方按需注入。
 */
export function uploadGearImage(
  filePath: string,
  hooks?: { onSuccess?: (url: string, durationMs: number) => void; onFailed?: (error: Error, durationMs: number) => void; onMirage?: (url: string, durationMs: number) => void },
): Promise<string> {
  return uploadFile({
    path: "/upload/gear-image",
    filePath,
    onSuccess: (data, durationMs) => hooks?.onSuccess?.(data.url as string, durationMs),
    onFailed: (error, durationMs) => hooks?.onFailed?.(error, durationMs),
    onMirage: (data, durationMs) => hooks?.onMirage?.(data.url as string, durationMs),
  }).then((r) => r.url);
}

/**
 * 选择一张图片并上传到服务器（供 photo 字段存储）。
 *
 * 流程：uni.chooseMedia 选图 → uni.compressImage 压缩 → 上传到服务器。
 * 用户取消选择时返回空字符串。
 */
export function choosePhoto(maxW = 900, quality = 0.8): Promise<string> {
  return new Promise((resolve, reject) => {
    uni.chooseMedia({
      count: 1,
      mediaType: ["image"],
      sizeType: ["compressed"],
      success: (res) => {
        const tempPath = res.tempFiles?.[0]?.tempFilePath;
        if (!tempPath) {
          resolve("");
          return;
        }
        uni.compressImage({
          src: tempPath,
          quality,
          compressedWidth: maxW,
          success: (cres) => {
            const target = cres.tempFilePath || tempPath;
            uploadGearImage(target)
              .then((url) => resolve(url))
              .catch((err) => reject(err));
          },
          fail: () => {
            // 压缩失败时直接上传原图
            uploadGearImage(tempPath)
              .then((url) => resolve(url))
              .catch((err) => reject(err));
          },
        });
      },
      fail: () => resolve(""),
    });
  });
}

/**
 * 游客态封面内容安全即检（仅检即弃，不落盘）。
 * 调用匿名端点 /api/upload/guest-gear-check，返回是否安全（true=放行）。
 * 网络/异常按 fail-open 处理：返回 true，保证本地点开可用性。
 */
export function guestCheckGearImage(filePath: string, code: string): Promise<boolean> {
  return uploadRaw<{ safe?: boolean }>({
    path: "/upload/guest-gear-check",
    filePath,
    formData: { code },
  })
    .then((d) => !!d.safe)
    .catch(() => true);
}

/**
 * 将本地图片文件读为 dataURL（base64）。
 * 用于游客态装备封面本地保存：选图后先压成 dataURL 存本地仓库，
 * 登录同步时再转临时文件走正式受检上传。
 */
export function compressToDataURL(filePath: string): Promise<string> {
  return new Promise((resolve, reject) => {
    try {
      const fs = uni.getFileSystemManager();
      fs.readFile({
        filePath,
        encoding: "base64",
        success: (r) => resolve(`data:image/jpeg;base64,${r.data as string}`),
        fail: (err) => reject(new Error(err.errMsg || "图片读取失败")),
      });
    } catch (e) {
      reject(e as Error);
    }
  });
}

/**
 * 安全返回上一页：若栈深不足（当前为首页）则跳转到 tabBar 首页。
 * 适用于 form 页面保存/删除后返回，避免 navigateBack 在栈底抛错。
 */
export function safeNavigateBack(fallbackUrl = "/pages/diary/diary"): void {
  const pages = getCurrentPages();
  if (pages.length > 1) {
    uni.navigateBack();
  } else {
    uni.switchTab({ url: fallbackUrl });
  }
}
