/**
 * 事件日志上报工具
 *
 * 四级日志：info / warn / error / fatal
 * 上报策略：
 * - error/fatal：实时上报（立即发送，不等待批量）
 * - info/warn：批量上报（防抖 3s 或 ≥5 条时触发）
 * - 上报失败不阻塞业务，本地缓存兜底，下次启动补发
 */

import { API_PREFIX, BASE_URL } from "@/config";
import { STORAGE_KEYS } from "@/constants/storage";

// ==================== 类型 ====================

export type LogLevel = "info" | "warn" | "error" | "fatal";
export type EventType = "network" | "business" | "crash" | "custom";

export interface EventLogPayload {
  level: LogLevel;
  type: EventType;
  traceId: string;
  action?: string;
  message: string;
  stack?: string;
  page?: string;
  extra?: Record<string, any>;
  deviceInfo?: Record<string, any>;
}

// ==================== 常量 ====================

const BATCH_FLUSH_INTERVAL_MS = 3000;
const BATCH_THRESHOLD = 5;
const MAX_PENDING_CACHE = 50;

// ==================== 状态 ====================

let pendingBatch: EventLogPayload[] = [];
let flushTimer: ReturnType<typeof setTimeout> | null = null;

// ==================== 工具 ====================

/** 获取设备信息 */
function getDeviceInfo(): Record<string, any> {
  try {
    const info = uni.getSystemInfoSync();
    return {
      platform: info.platform,
      model: info.model,
      system: info.system,
      screenWidth: info.screenWidth,
      screenHeight: info.screenHeight,
      brand: info.brand,
    };
  } catch {
    return {};
  }
}

/** 获取当前页面路径 */
function getCurrentPage(): string {
  try {
    const pages = getCurrentPages();
    const page = pages[pages.length - 1] as any;
    return page?.route || "";
  } catch {
    return "";
  }
}

/** 追加到本地缓存（上报失败时调用） */
function appendToPending(payload: EventLogPayload): void {
  try {
    const raw = uni.getStorageSync(STORAGE_KEYS.eventLogPending) as string;
    const cached: EventLogPayload[] = raw ? JSON.parse(raw) : [];
    cached.push(payload);
    if (cached.length > MAX_PENDING_CACHE) {
      cached.splice(0, cached.length - MAX_PENDING_CACHE);
    }
    uni.setStorageSync(STORAGE_KEYS.eventLogPending, JSON.stringify(cached));
  } catch {
    // 忽略缓存失败
  }
}

/** 补发本地缓存的离线事件 */
export function flushPendingEvents(): void {
  try {
    const raw = uni.getStorageSync(STORAGE_KEYS.eventLogPending) as string;
    if (!raw) return;
    const cached: EventLogPayload[] = JSON.parse(raw);
    if (!cached.length) return;
    uni.removeStorageSync(STORAGE_KEYS.eventLogPending);
    cached.forEach((p) => flushOne(p));
  } catch {
    // 忽略
  }
}

/** 上报单条事件日志 */
function flushOne(payload: EventLogPayload): void {
  // 延迟导入，避免循环依赖（stores/auth → services/auth → request → eventLogger → stores/auth）
  const { useAuthStore } = require("@/stores/auth");
  const authStore = useAuthStore();
  const token = uni.getStorageSync(STORAGE_KEYS.token) as string;

  const body: Record<string, any> = {
    level: payload.level,
    type: payload.type,
    trace_id: payload.traceId,
    action: payload.action || null,
    message: payload.message,
    stack: payload.stack || "",
    page: payload.page ?? getCurrentPage(),
    extra: payload.extra || {},
    device_info: payload.deviceInfo || getDeviceInfo(),
    client_time: Date.now(),
  };

  if (authStore.isLoggedIn && authStore.user) {
    body.extra.user_id = authStore.user.id;
  }

  const fullUrl = `${BASE_URL}${API_PREFIX}/events`;
  uni.request({
    url: fullUrl,
    method: "POST",
    data: body,
    header: {
      "Content-Type": "application/json",
      ...(token ? { 'X-Auth-Token': token } : {}),
    },
    timeout: 5000,
    success() {
      // 静默成功
    },
    fail() {
      appendToPending(payload);
    },
  });
}

/** 批量防抖 flush（info/warn 使用） */
function batchFlush(): void {
  if (flushTimer) clearTimeout(flushTimer);
  flushTimer = setTimeout(() => {
    flushTimer = null;
    const batch = [...pendingBatch];
    pendingBatch = [];
    batch.forEach(flushOne);
  }, BATCH_FLUSH_INTERVAL_MS);
}

// ==================== 公开 API ====================

/** 生成唯一 trace ID（毫秒时间戳 + 随机后缀） */
export function createTraceId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

/** 记录信息事件（批量上报） */
export function logInfo(message: string, extra?: Record<string, any>, action?: string, traceId?: string): void {
  const currentTraceId = traceId || createTraceId();
  pendingBatch.push({
    level: "info",
    type: "business",
    traceId: currentTraceId,
    action,
    message,
    extra,
  });
  batchFlush();
}

/** 记录警告事件（批量上报，≥5 条立即触发） */
export function logWarn(message: string, extra?: Record<string, any>, action?: string, traceId?: string): void {
  const currentTraceId = traceId || createTraceId();
  pendingBatch.push({
    level: "warn",
    type: "business",
    traceId: currentTraceId,
    action,
    message,
    extra,
  });
  if (pendingBatch.length >= BATCH_THRESHOLD) {
    batchFlush();
    pendingBatch = [];
  } else {
    batchFlush();
  }
}

/** 记录错误事件（实时上报） */
export function logError(
  message: string,
  extra?: Record<string, any>,
  action?: string,
  stack?: string,
  traceId?: string,
): void {
  const currentTraceId = traceId || createTraceId();
  flushOne({
    level: "error",
    type: "business",
    traceId: currentTraceId,
    action,
    message,
    stack: stack || "",
    extra,
  });
}

/** 记录致命事件（实时上报） */
export function logFatal(
  message: string,
  extra?: Record<string, any>,
  stack?: string,
  traceId?: string,
): void {
  const currentTraceId = traceId || createTraceId();
  flushOne({
    level: "fatal",
    type: "crash",
    traceId: currentTraceId,
    message,
    stack: stack || "",
    extra,
  });
}
