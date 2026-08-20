<template>
  <page-meta :page-style="themeStyle" :background-color="themeBg" />
  <view class="analyze-page">
    <view class="analyze-body">
      <!-- ① 选择分析类型 -->
      <view class="form-card">
        <view class="card-title-row">
          <text class="step-badge">1</text>
          <text class="card-title">选择分析类型</text>
        </view>
        <view class="mode-pills">
          <view
            class="mode-pill press-btn"
            :class="mode === 'single' ? 'mode-pill--active' : 'mode-pill--inactive'"
            @tap="setMode('single')"
          >单次挥拍</view>
          <view
            class="mode-pill press-btn"
            :class="mode === 'full' ? 'mode-pill--active' : 'mode-pill--inactive'"
            @tap="setMode('full')"
          >综合分析</view>
        </view>
        <Seg
          class="kind-seg"
          v-model="kind"
          :options="kindOptions"
        />
        <text class="form-hint">
          {{ mode === "single"
            ? "上传包含一次完整挥拍的视频，裁剪出片段并停留到「击球瞬间」，再点开始分析"
            : "上传多段训练/对拉片段（可时间轴裁剪拼接），将综合分析动作、节奏与战术" }}
        </text>
      </view>

      <!-- ② 上传视频 -->
      <view class="form-card">
        <view class="card-title-row">
          <text class="step-badge">2</text>
          <text class="card-title">上传视频</text>
        </view>

        <view v-if="!videoPath" class="upload-box press-btn" @tap="chooseVideo">
          <text class="upload-icon">🎥</text>
          <text class="upload-text">点击选择视频</text>
          <text class="upload-sub">支持 mp4 / mov，整片最长 3 分钟</text>
          <text class="upload-sub">单次片段 ≤ 15 秒 · 综合片段 ≤ 90 秒</text>
        </view>
        <view v-else class="video-box">
          <video
            id="swingVideo"
            class="video-el"
            :src="videoPath"
            controls
            @loadedmetadata="onVideoMeta"
            @play="isPlaying = true"
             @pause="isPlaying = false; onVideoTimeUpdate($event)"
            @timeupdate="onVideoTimeUpdate"
          />
          <view v-if="mode === 'single'" class="hit-row">
            <view class="hit-info">
              <text class="hit-label">击球瞬间（片段内）</text>
              <text class="hit-value">{{ hitTimeText }}</text>
            </view>
            <view class="hit-btn press-btn" @tap="clearHitTime">清除击球瞬间</view>
          </view>
          <text class="video-sub">
            {{ mode === "single" ? "🧭 用下方时间轴拖动播放头到击球瞬间，或视频内直接暂停定位" : "🧭 可在下方时间轴添加多个片段拼接分析" }}
          </text>

          <!-- 时间轴剪辑 - 类似剪映风格 -->
          <view v-if="videoDuration > 0" class="trim-section">
            <view class="trim-head">
              <text class="trim-title">时间轴剪辑</text>
              <text class="trim-meta">{{ trimMetaText }}</text>
            </view>

            <!-- 缩放控件（时间轴上方两侧，放大镜图标） -->
            <view class="tl-zoom-controls">
              <view class="tl-zoom-btn press-btn" @tap="zoomOut">
                <view class="tl-glass"></view>
                <view class="tl-glass-badge">−</view>
              </view>
              <view class="tl-zoom-btn press-btn" @tap="zoomIn">
                <view class="tl-glass"></view>
                <view class="tl-glass-badge">＋</view>
              </view>
            </view>

            <!-- 时间刻度（固定在容器上，以播放头为 0 参考） -->
            <view class="tl-ruler">
              <text v-for="t in rulerTicks" :key="t" class="tl-ruler-tick" :style="{ left: containerX(t) + 'px' }">{{ fmtTime(t) }}</text>
            </view>

            <!-- 视频轨道容器 -->
            <view
              class="tl-track-container"
              @touchstart="onTrackTouchStart"
              @touchmove="onTrackTouchMove"
              @touchend="onTrackTouchEnd"
              @touchcancel="onTrackTouchEnd"
            >
              <!-- 视频轨道（可拖动，宽度随视频时长与缩放变化） -->
              <view
                class="tl-track"
                :style="{
                  width: trackWidth + 'px',
                  transform: `translateX(${trackOffset}px)`
                }"
              >
                <!-- 已选片段色块 -->
                <view
                  v-for="(sg, i) in segments"
                  :key="sg.key"
                  class="tl-clip"
                  :style="clipStyle(sg)"
                  @tap.stop="centerOnSegment(i)"
                >
                  <text class="tl-clip-label">{{ i + 1 }}</text>
                </view>
                <!-- 开放起点标记 -->
                <view
                  v-if="pendingStart !== null"
                  class="tl-pending-mark"
                  :style="{ left: t2x(pendingStart) + 'px' }"
                ></view>
              </view>

              <!-- 中间播放头（固定竖线） -->
              <view class="tl-playhead"></view>
            </view>

            <view class="timeline-info">
              <text class="tl-info-time">▶ {{ fmtTime(playhead) }}s / {{ fmtTime(videoDuration) }}s</text>
              <text class="tl-info-zoom">拖动轨道选择帧 · ＋/− 缩放</text>
            </view>

            <view class="trim-actions">
              <view
                class="trim-btn press-btn"
                :class="{ 'trim-btn--pending': pendingStart !== null }"
                @tap="toggleSegment"
              >
                {{ pendingStart === null ? `设置起点 @ ${fmtTime(playhead)}s` : `设置终点 @ ${fmtTime(playhead)}s` }}
              </view>
              <view
                v-if="segments.length || pendingStart !== null"
                class="trim-undo press-btn"
                @tap="resetSegments"
              >重置</view>
            </view>

            <view v-if="segments.length" class="seg-list">
              <view v-for="(sg, i) in segments" :key="sg.key" class="seg-chip" @tap="removeSegment(i)">
                <text class="seg-chip-label">段{{ i + 1 }}</text>
                <text class="seg-chip-time">{{ fmtTime(sg.start) }}–{{ fmtTime(sg.end) }}s</text>
                <text class="seg-chip-del">✕</text>
              </view>
              <text class="seg-total">总 {{ fmtTime(totalConcat) }}s / 上限 {{ modeLimit }}s</text>
            </view>

            <text v-if="warnMsg" class="trim-warn">{{ warnMsg }}</text>
            <text v-if="needTrimHint" class="trim-need">{{ needTrimHint }}</text>
          </view>
        </view>
      </view>

      <!-- ③ 开始分析 -->
      <view
        class="analyze-btn press-btn"
        :class="{ 'analyze-btn--disabled': !videoPath || analyzing }"
        @tap="startAnalysis"
      >
        <text v-if="analyzing">分析中，请稍候…</text>
        <text v-else>开始分析</text>
      </view>
      <text v-if="analyzing" class="analyze-progress">{{ progress }}</text>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from "vue";

import Seg from "@/components/Seg.vue";
import { useThemeStyle } from "@/composables/useTheme";
import {
  analyzePose,
  analyzeSwing,
  createAnalysis,
  uploadVideo,
} from "@/services/data";
import type { AnalysisKind, AnalysisPose, AnalysisReport } from "@/types";
import { ANALYSIS_KINDS, todayStr } from "@/utils";
import { createTraceId, logError, logInfo } from "@/utils/eventLogger";
import { isUserCancel, isRuntimePermissionDenied } from "@/utils/privacy";

const { themeStyle, themeBg } = useThemeStyle();

type Mode = "single" | "full";

interface TrimSegment {
  key: number;
  start: number;
  end: number;
}

// 与后端 video_service 对齐的裁剪约束（时长上限与整片上传上限一致，不再按模式收紧）
const UPLOAD_MAX = 180;
const MODE_LIMIT: Record<Mode, number> = { single: 180, full: 180 };
const MAX_SEGMENTS: Record<Mode, number> = { single: 1, full: 8 };
const MIN_SEGMENT = 0.6;
const MIN_ZOOM_SPAN = 0.5; // 放大极限：0.5s 满屏（接近逐帧）
const INIT_SPAN = 4; // 初始视野：约显示 4 秒（保证缩小/放大均有明显范围）
const TRACK_PPS = 80; // 兜底每秒像素（measureBar 前）
let zoomInitialized = false; // 缩放是否已按容器宽度初始化

const mode = ref<Mode>("single");
const kind = ref<AnalysisKind>("正手");
const videoPath = ref("");
const videoDuration = ref(0);
const analyzing = ref(false);
const progress = ref("");
const hitTime = ref(0);
const warnMsg = ref("");
const videoReady = ref(false);
const isPlaying = ref(false);

// ============ 时间轴状态（剪映式：轨道可拖动 + 固定中间播放头） ============
const segments = ref<TrimSegment[]>([]);
const pendingStart = ref<number | null>(null); // 当前开放的起点，null 表示无开放段
const pps = ref(TRACK_PPS); // 每秒像素（轨道缩放比例，越大越放大）
const playhead = ref(0); // 播放头时间（秒），固定在容器中间
const barWidth = ref(0);
const barLeft = ref(0);
const barTop = ref(0);
const barHeight = ref(60);
let segKey = 0;

let videoCtx: UniApp.VideoContext | null = null;
let dragMode: "none" | "track" | "pinch" = "none";
let pinchDist = 0;
let pinchStartPps = TRACK_PPS;
let lastPanX = 0;
let lastSeekTs = 0;

// 轨道偏移量（px）：使播放头始终显示在容器中间
const trackOffset = computed(() => barWidth.value / 2 - playhead.value * pps.value);

// 缩放范围：最大视野=整片、最小视野=MIN_ZOOM_SPAN 秒
const minPps = computed(() => (videoDuration.value && barWidth.value ? barWidth.value / videoDuration.value : 1));
const maxPps = computed(() => (barWidth.value ? barWidth.value / MIN_ZOOM_SPAN : 100));

// 轨道总宽度（像素）
const trackWidth = computed(() => videoDuration.value * pps.value);

// 时间刻度步进（随缩放自适应：保证相邻刻度至少 40px 间距）
const rulerStep = computed(() => {
  if (!barWidth.value || !pps.value) return 1;
  for (const s of [0.1, 0.2, 0.5, 1, 2, 5, 10, 15, 30, 60]) {
    if (s * pps.value >= 40) return s;
  }
  return 60;
});

// 当前可见时间窗内的时间刻度标记（超出容器不渲染，避免堆积）
const rulerTicks = computed(() => {
  const dur = videoDuration.value;
  const p = pps.value;
  if (!dur || !barWidth.value || !p) return [];
  const step = rulerStep.value;
  const halfSpan = barWidth.value / 2 / p;
  const firstT = Math.max(0, playhead.value - halfSpan);
  const lastT = Math.min(dur, playhead.value + halfSpan);
  const first = Math.ceil(firstT / step) * step;
  const last = Math.floor(lastT / step) * step;
  const arr: number[] = [];
  for (let t = first; t <= last + 1e-6; t += step) {
    arr.push(Math.round(t * 10) / 10);
  }
  return arr;
});

const kindOptions = computed(() =>
  mode.value === "full"
    ? ANALYSIS_KINDS
    : (ANALYSIS_KINDS.filter((k) => k !== "综合") as readonly string[]),
);

const modeLimit = computed(() => MODE_LIMIT[mode.value]);
const hitTimeText = computed(() =>
  hitTime.value > 0 ? `${hitTime.value.toFixed(1)}s` : "未设置（默认为拼接视频中点）",
);

const totalConcat = computed(() =>
  segments.value.reduce((sum, s) => sum + (s.end - s.start), 0),
);
const trimmed = computed(() => segments.value.length > 0);
const needTrimHint = computed(() => {
  if (videoDuration.value <= modeLimit.value) return "";
  return trimmed.value
    ? ""
    : `视频 ${videoDuration.value.toFixed(0)}s 超过 ${modeLimit.value}s 上限，请在下方时间轴截取片段`;
});
const trimMetaText = computed(() => {
  if (!segments.value.length) return "整片直传";
  return `${segments.value.length}/${MAX_SEGMENTS[mode.value]} 段 · ${totalConcat.value.toFixed(1)}s`;
});

onMounted(() => {
  videoCtx = uni.createVideoContext("swingVideo");
});

// ============ 模式切换 ============
function setMode(m: Mode) {
  mode.value = m;
  resetSegments();
  resetTimelineBits();
  if (m === "full") hitTime.value = 0;
}

function resetTimelineBits() {
  hitTime.value = 0;
  warnMsg.value = "";
}

// ============ 选择视频 ============
function chooseVideo() {
  const traceId = createTraceId();
  logInfo("选择视频", { trace_id: traceId }, "choose_video", traceId);
  uni.chooseVideo({
    // 不传 maxDuration：微信选择器硬上限 60s，传入会前置报错；相册长片由下方 180s 预检查兜底
    sourceType: ["album", "camera"],
    success: (res) => {
      const dur = Number(res.duration) || 0;
      if (dur > UPLOAD_MAX) {
        uni.showToast({ title: `视频 ${Math.round(dur)}s 超过 3 分钟，请先在相册裁剪`, icon: "none" });
        logInfo("视频超长被拒", { trace_id: traceId, duration: dur }, "choose_video_too_long", traceId);
        return;
      }
      videoPath.value = res.tempFilePath;
      videoDuration.value = dur;
      hitTime.value = 0;
      resetSegments();
      playhead.value = 0;
      pps.value = TRACK_PPS;
      zoomInitialized = false;
      measureBar();
      logInfo("视频选择成功", { trace_id: traceId, duration: dur }, "choose_video_success", traceId);
    },
    fail: (err) => {
      console.error("[chooseVideo] 失败", err);
      if (isUserCancel(err)) {
        logInfo("用户取消选择视频", { trace_id: traceId }, "choose_video_cancel", traceId);
      } else if (isRuntimePermissionDenied(err)) {
        logError("选择视频权限被拒绝", { trace_id: traceId, error: err.errMsg }, "choose_video_denied", undefined, traceId);
        uni.showToast({ title: "需要授权使用相册/相机功能", icon: "none" });
      } else {
        logError("选择视频失败", { trace_id: traceId, error: err.errMsg }, "choose_video_failed", undefined, traceId);
        uni.showToast({ title: "选择视频失败，请重试", icon: "none" });
      }
    },
  });
}

function onVideoMeta(e: any) {
  const d = e?.detail?.duration;
  if (typeof d === "number" && d > 0 && !videoDuration.value) {
    videoDuration.value = d;
  }
  // 视频元素此时已渲染，重新绑定上下文保证 seek 预览可用
  videoCtx = uni.createVideoContext("swingVideo");
  videoReady.value = true;
}

// ============ 时间轴坐标换算 ============
function measureBar() {
  nextTick(() => {
    uni.createSelectorQuery()
      .select(".tl-track-container")
      .boundingClientRect((rect: any) => {
        if (rect && rect.width > 0) {
          barWidth.value = rect.width;
          barLeft.value = rect.left;
          barTop.value = rect.top;
          if (rect.height > 0) barHeight.value = rect.height;
          // 首次按容器宽度初始化缩放：初始显示约 min(duration, INIT_SPAN) 秒，
          // 使缩小可达全览、放大可达帧级，缩放范围感知明显
          if (!zoomInitialized && videoDuration.value > 0) {
            const initSpan = Math.min(videoDuration.value, INIT_SPAN);
            pps.value = Math.max(rect.width / initSpan, rect.width / videoDuration.value);
            zoomInitialized = true;
          }
        }
      })
      .exec();
  });
}

/** 时间(秒) → 轨道内像素位置（相对轨道起点） */
function t2x(t: number): number {
  return t * pps.value;
}

/** 时间(秒) → 容器内像素位置（相对容器左端，含轨道偏移） */
function containerX(t: number): number {
  return barWidth.value / 2 + (t - playhead.value) * pps.value;
}

/** 容器内像素 → 时间(秒) */
function x2t(x: number): number {
  if (!barWidth.value || !pps.value) return 0;
  return playhead.value + (x - barWidth.value / 2) / pps.value;
}

function clampT(t: number): number {
  const dur = videoDuration.value;
  return Math.min(Math.max(0, t), Math.max(0, dur));
}

/** 设置播放头时间（夹紧） */
function setPlayhead(t: number) {
  playhead.value = clampT(t);
}

/** 点击选中的片段 → 播放头移到片段中点并预览 */
function centerOnSegment(i: number) {
  const sg = segments.value[i];
  if (!sg) return;
  setPlayhead((sg.start + sg.end) / 2);
  flushPlayhead();
}

// ============ 时间轴手势：拖动轨道 + 双指捏合缩放 ============
function onTrackTouchStart(e: any) {
  const touches = e.touches || [];
  if (touches.length >= 2) {
    dragMode = "pinch";
    pinchDist = touchDist(touches);
    pinchStartPps = pps.value;
    return;
  }
  const touch = touches[0];
  if (!touch) return;
  if (dragMode === "pinch") {
    // 双指抬剩单指：记录新起点，仍按拖动轨道处理
  }
  dragMode = "track";
  lastPanX = touch.clientX;
}

function onTrackTouchMove(e: any) {
  const touches = e.touches || [];
  if (touches.length >= 2) {
    if (dragMode !== "pinch") {
      dragMode = "pinch";
      pinchDist = touchDist(touches);
      pinchStartPps = pps.value;
    }
    applyPinch(touchDist(touches));
    return;
  }
  if (touches.length === 1) {
    const x = touches[0].clientX;
    if (dragMode === "pinch") {
      dragMode = "track";
      lastPanX = x;
    }
    if (dragMode === "track") {
      const dx = x - lastPanX;
      if (dx !== 0) {
        setPlayhead(playhead.value - dx / pps.value);
        lastPanX = x;
        throttleSeek(playhead.value);
      }
    }
  }
}

function onTrackTouchEnd() {
  const wasTrack = dragMode === "track";
  dragMode = "none";
  pinchDist = 0;
  if (wasTrack) flushPlayhead();
}

// ============ 缩放控件（放大 / 缩小按钮） ============
const ZOOM_STEP = 1.5; // 每次缩放倍率

function zoomIn() {
  if (!barWidth.value || !videoDuration.value) return;
  const newPps = Math.min(maxPps.value, pps.value * ZOOM_STEP);
  if (newPps === pps.value) return;
  pps.value = newPps;
}

function zoomOut() {
  if (!barWidth.value || !videoDuration.value) return;
  const newPps = Math.max(minPps.value, pps.value / ZOOM_STEP);
  if (newPps === pps.value) return;
  pps.value = newPps;
}

function touchDist(touches: any[]): number {
  const a = touches[0];
  const b = touches[1];
  if (!a || !b) return 0;
  return Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY);
}

function applyPinch(dist: number) {
  if (!barWidth.value || dist <= 0 || pinchDist <= 0) return;
  const factor = dist / pinchDist; // 手指张开 → 放大
  const newPps = Math.min(Math.max(pinchStartPps * factor, minPps.value), maxPps.value);
  pps.value = newPps;
  pinchDist = dist;
}

function throttleSeek(t: number) {
  const now = Date.now();
  if (now - lastSeekTs < 50) return;
  lastSeekTs = now;
  seekPreview(t);
}

/** seek + （暂停态下）play/pause 强制刷新目标帧 */
function seekPreview(t: number) {
  if (!videoCtx || !videoReady.value) return;
  try {
    videoCtx.seek(t);
    if (!isPlaying.value) {
      videoCtx.play();
      videoCtx.pause();
    }
  } catch {
    /* 视频上下文未就绪时忽略 */
  }
}

/** 松手后强制刷新一次目标帧 */
function flushPlayhead() {
  seekPreview(playhead.value);
}

// ============ 片段裁剪控制（支持多段） ============
/** 切换段状态：开段 → 闭段，或开新段 */
function toggleSegment() {
  const t = playhead.value;
  warnMsg.value = "";

  if (pendingStart.value === null) {
    // 开新段
    if (segments.value.length >= MAX_SEGMENTS[mode.value]) {
      warnMsg.value = mode.value === "full" ? "最多 8 段，请先删除已有片段" : "单次挥拍仅支持 1 段";
      return;
    }
    // single 模式：已有片段时不允许新开段
    if (mode.value === "single" && segments.value.length > 0) {
      warnMsg.value = "单次挥拍仅支持 1 段，请先重置";
      return;
    }
    pendingStart.value = t;
    return;
  }

  // 闭段
  const start = pendingStart.value;
  if (t - start < MIN_SEGMENT) {
    warnMsg.value = "片段最短 0.6 秒";
    return;
  }
  segments.value.push({ key: segKey++, start, end: t });
  pendingStart.value = null;
}

function removeSegment(i: number) {
  segments.value.splice(i, 1);
  pendingStart.value = null;
  warnMsg.value = "";
}

function resetSegments() {
  segments.value = [];
  pendingStart.value = null;
  warnMsg.value = "";
}

// ============ 样式 ============
function clipStyle(sg: TrimSegment) {
  const left = t2x(sg.start);
  const width = t2x(sg.end) - left;
  return { left: `${left}px`, width: `${width}px` };
}

// ============ 击球瞬间（片段内相对时间） ============
/** 原始时间 → 拼接后片段内相对时间；落在片段间隙返回 null */
function toConcatTime(t: number): number | null {
  if (!segments.value.length) return t;
  let prefix = 0;
  for (const s of segments.value) {
    if (t <= s.end) {
      if (t >= s.start) return prefix + (t - s.start);
      return null;
    }
    prefix += s.end - s.start;
  }
  return null;
}

/** 原始时间 → 所在片段序号；未命中片段返回 -1 */
function segmentIndexAt(t: number): number {
  for (let i = 0; i < segments.value.length; i++) {
    if (t >= segments.value[i].start && t <= segments.value[i].end) return i;
  }
  return -1;
}

/** 视频播放时自动更新击球瞬间时间 */
function onVideoTimeUpdate(e: any) {
  // 播放头已自动跟随，此函数保留用于兼容（可选）
}

/** 播放头变化时自动更新击球瞬间 */
watch(playhead, (t) => {
  if (mode.value !== "single") return;
  const idx = segmentIndexAt(t);
  if (idx < 0) {
    hitTime.value = 0;
    return;
  }
  const concatT = toConcatTime(t);
  if (concatT !== null) hitTime.value = concatT;
});

function clearHitTime() {
  hitTime.value = 0;
  warnMsg.value = "";
}

// ============ 开始分析 ============
async function startAnalysis() {
  if (analyzing.value || !videoPath.value) return;
  const traceId = createTraceId();
  logInfo("开始AI分析", { trace_id: traceId, mode: mode.value, kind: kind.value }, "analysis_started", traceId);

  const dur = videoDuration.value;
  if (!trimmed.value) {
    if (dur <= 0) {
      // 时长未加载（chooseVideo/loadedmetadata 均未就绪）时不能盲目放行，否则会让用户撞上后端"整片超限"报错
      uni.showToast({ title: "视频时长未加载，请稍候或重新选择视频后在时间轴截取片段", icon: "none" });
      return;
    }
    if (dur > modeLimit.value) {
      // modeLimit 现与整片上传上限一致：此分支仅在选择器时长校验被绕过时兜底
      uni.showToast({ title: `视频超过 ${UPLOAD_MAX} 秒上限，请先在相册裁剪后再上传`, icon: "none" });
      return;
    }
  }

  analyzing.value = true;
  try {
    const formData: { mode: string; kind: string; hit_time?: string; cuts?: string } = {
      mode: mode.value,
      kind: kind.value,
      hit_time: mode.value === "single" && hitTime.value > 0 ? String(hitTime.value.toFixed(2)) : "",
    };

    if (trimmed.value) {
      formData.cuts = JSON.stringify(
        segments.value.map((s) => ({ start: round2(s.start), end: round2(s.end) })),
      );
      logInfo("携带裁剪片段上传", { trace_id: traceId, cuts: formData.cuts }, "analysis_with_cuts", traceId);
    }

    // 0. 检查视频文件是否存在（临时文件可能已被系统回收）
    const fs = uni.getFileSystemManager();
    const fileExists = await new Promise<boolean>((resolve) => {
      fs.access({
        path: videoPath.value,
        success: () => resolve(true),
        fail: () => resolve(false),
      });
    });
    if (!fileExists) {
      videoPath.value = "";
      throw new Error("视频文件已失效，请重新选择");
    }

    // 1. 上传 + 抽帧（75-2，含裁切拼接）
    progress.value = "上传视频并抽取关键帧…";
    const uploaded = await uploadVideo(videoPath.value, formData);

    // 2. AI 六维评分 与 姿态测量 并行执行（Step 83：每次分析都跑姿态，含骨架绘制）
    progress.value = "教练正在分析动作与姿态（约 15-90 秒）…";
    const [aiResult, poseResult] = await Promise.allSettled([
      analyzeSwing(uploaded.frames, kind.value, mode.value),
      analyzePose(uploaded.frames, {
        videoUrl: uploaded.video_url,
        saveSkeleton: true,
        duration: uploaded.duration,
        frameRate: uploaded.frame_rate,
      }),
    ]);

    const report =
      aiResult.status === "fulfilled" ? aiResult.value : ({} as AnalysisReport);
    const pose: AnalysisPose | null =
      poseResult.status === "fulfilled" && poseResult.value.detected
        ? {
            detected: true,
            metrics: poseResult.value.metrics ?? undefined,
            skeleton_frames: poseResult.value.skeleton_frames,
            skeleton_video_url: poseResult.value.skeleton_video_url,
            skeleton_thumb: poseResult.value.skeleton_thumb,
          }
        : null;

    // 姿态测量追加进摘要，提升列表/报告可读性
    const enrichedReport = { ...report };
    if (pose?.metrics) {
      enrichedReport.summary = `${report.summary || ""} 姿态：肘角 ${Math.round(pose.metrics.elbowAngle)}° · 膝角 ${Math.round(pose.metrics.kneeAngle)}° · 躯干倾斜 ${Math.round(pose.metrics.trunkLean)}°`;
    }

    // 3. 落库（75-4，封面优先用骨架标注帧）
    const analysis = await createAnalysis({
      date: todayStr(),
      kind: kind.value,
      mode: mode.value,
      score: enrichedReport.score || 0,
      summary: enrichedReport.summary,
      ntrp: enrichedReport.ntrp,
      report: enrichedReport,
      thumb: pose?.skeleton_thumb || uploaded.thumbnail,
      video_url: uploaded.video_url,
      pose: pose ?? undefined,
    });

    uni.redirectTo({ url: `/pages/coach/report?id=${analysis.id}` });
    logInfo("AI分析完成", { trace_id: traceId, analysis_id: analysis.id, kind: kind.value, mode: mode.value, has_pose: !!pose }, "analysis_completed", traceId);
  } catch (e) {
    const msg = e instanceof Error ? e.message : "分析失败，请重试";
    logError("AI分析失败", { trace_id: traceId, error: msg, kind: kind.value, mode: mode.value }, "analysis_failed", undefined, traceId);
    uni.showToast({ title: msg, icon: "none" });
  } finally {
    analyzing.value = false;
    progress.value = "";
  }
}

function round2(n: number): number {
  return Math.round(n * 100) / 100;
}

function fmtTime(s: number): string {
  return (Number.isFinite(s) ? s : 0).toFixed(1);
}
</script>

<style scoped lang="scss">
.analyze-page {
  min-height: 100vh;
  background-color: var(--color-page-bg, #F2F2EF);
}

.analyze-body {
  padding: $space-lg;
  padding-top: $space-xl;
  display: flex;
  flex-direction: column;
  gap: $space-md;
}

.form-card {
  background-color: var(--color-card, #FFFFFF);
  border-radius: $radius-card;
  padding: $space-lg;
  box-shadow: $shadow-card;
}

.card-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: $space-md;
}

.step-badge {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background-color: var(--color-accent, #C8DA2B);
  color: $color-ink;
  font-size: 12px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.card-title {
  font-size: $font-size-base;
  font-weight: 600;
  color: $color-ink;
}

.mode-pills {
  display: flex;
  gap: $space-sm;
  margin-bottom: $space-md;
}

.mode-pill {
  flex: 1;
  text-align: center;
  padding: 10px 0;
  border-radius: $radius-card;
  font-size: 14px;

  &--active {
    background-color: $color-olive;
    color: $color-white;
    font-weight: 500;
  }

  &--inactive {
    background-color: var(--color-page-bg, #F2F2EF);
    color: $color-olive-light;
  }
}

.kind-seg {
  margin-bottom: $space-md;
}

.form-hint {
  display: block;
  font-size: 12px;
  color: $color-olive-light;
  line-height: 1.6;
}

// ========== 上传区 ==========
.upload-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 0;
  border: 2px dashed #d8d8d0;
  border-radius: $radius-card;
}

.upload-icon {
  font-size: 40px;
}

.upload-text {
  margin-top: 8px;
  font-size: 14px;
  font-weight: 500;
  color: $color-ink;
}

.upload-sub {
  margin-top: 4px;
  font-size: 12px;
  color: $color-olive-light;
  text-align: center;
  padding: 0 20px;
}

.video-box {
  border-radius: $radius-card;
  overflow: hidden;
}

.video-el {
  width: 100%;
  border-radius: $radius-card;
  background-color: $color-olive;
}

.hit-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: $space-md;
  margin-top: $space-md;
}

.hit-info {
  flex: 1;
  min-width: 0;
}

.hit-label {
  display: block;
  font-size: 12px;
  color: $color-olive-light;
}

.hit-value {
  display: block;
  margin-top: 2px;
  font-size: 15px;
  font-weight: 600;
  color: $color-ink;
}

.hit-btn {
  background-color: var(--color-accent, #C8DA2B);
  color: $color-ink;
  font-size: 13px;
  font-weight: 500;
  padding: 8px 16px;
  border-radius: 9999px;
}

.video-sub {
  display: block;
  margin-top: $space-sm;
  font-size: 12px;
  color: $color-olive-light;
}

// ========== 时间轴剪辑 ==========
.trim-section {
  margin-top: $space-md;
  padding-top: $space-md;
  border-top: 1px dashed #e0e0d8;
}

.trim-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: $space-sm;
}

.trim-title {
  font-size: 14px;
  font-weight: 600;
  color: $color-ink;
}

.trim-meta {
  font-size: 12px;
  color: $color-olive-light;
}

// ========== 时间轴剪辑 ==========
.tl-zoom-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.tl-zoom-btn {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background-color: rgba(255, 255, 255, 0.85); /* 半透明白色背景 */
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12);
  position: relative;
}

.tl-glass {
  width: 18px;
  height: 18px;
  border: 2.5px solid var(--color-olive-light, #6b7c2a);
  border-radius: 50%;
  position: relative;
  box-sizing: border-box;
  flex-shrink: 0;

  // 手柄
  &::after {
    content: "";
    position: absolute;
    width: 8px;
    height: 3px;
    background: var(--color-olive-light, #6b7c2a);
    border-radius: 2px;
    transform: rotate(45deg);
    right: -8px;
    bottom: -3px;
  }
}

.tl-glass-badge {
  position: absolute;
  top: -3px;
  right: -3px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background-color: var(--color-accent, #C8DA2B);
  color: $color-ink;
  font-size: 12px;
  font-weight: 700;
  line-height: 16px;
  text-align: center;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
}

.tl-ruler {
  position: relative;
  height: 20px;
  margin-bottom: 4px;
}

.tl-ruler-tick {
  position: absolute;
  top: 0;
  font-size: 11px;
  font-weight: 600;
  color: $color-olive-light;
  transform: translateX(-50%);
  white-space: nowrap;

  &::after {
    content: "";
    position: absolute;
    top: 14px;
    left: 50%;
    width: 1px;
    height: 6px;
    background: #c8c8c0;
    transform: translateX(-50%);
  }
}

.tl-track-container {
  position: relative;
  height: 60px;
  border-radius: 8px;
  background-color: var(--color-page-bg, #F2F2EF);
  overflow: hidden;
}

.tl-track {
  position: absolute;
  top: 0;
  left: 0;
  height: 100%;
  min-width: 100%;
  box-sizing: border-box;
  border-right: 1px dashed #d8d8d0;
}

.tl-clip {
  position: absolute;
  top: 5px;
  bottom: 5px;
  border-radius: 6px;
  background: rgba(var(--color-accent-rgb, 200, 218, 43), 0.55);
  border: 1px solid var(--color-accent-dark, #A8B822);
  display: flex;
  align-items: center;
  justify-content: flex-start;
  padding-left: 4px;
  box-sizing: border-box;
}

.tl-clip-label {
  font-size: 10px;
  font-weight: 700;
  color: $color-ink;
}

.tl-pending-mark {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 2px;
  background: var(--color-accent, #C8DA2B);
  transform: translateX(-1px);

  &::after {
    content: "▶";
    position: absolute;
    top: 4px;
    left: 50%;
    transform: translateX(-50%);
    font-size: 10px;
    color: var(--color-accent, #C8DA2B);
  }
}

.tl-playhead {
  position: absolute;
  top: 0;
  bottom: 0;
  left: 50%;
  width: 2px;
  background: var(--color-accent-dark, #A8B822);
  box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.8);
  transform: translateX(-1px);
  z-index: 10;

  &::before {
    content: "";
    position: absolute;
    top: -4px;
    left: -5px;
    width: 12px;
    height: 12px;
    border-radius: 50% 50% 50% 0;
    background: var(--color-accent-dark, #A8B822);
    border: 2px solid $color-white;
    transform: rotate(-45deg);
  }
}

.timeline-info {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 6px;
}

.tl-info-time {
  font-size: 11px;
  color: $color-ink;
  font-variant-numeric: tabular-nums;
}

.tl-info-zoom {
  font-size: 11px;
  color: $color-olive-light;
}

.trim-actions {
  display: flex;
  align-items: center;
  gap: $space-sm;
  margin-top: $space-sm;
}

.trim-btn {
  flex: 1;
  text-align: center;
  background-color: var(--color-accent, #C8DA2B);
  color: $color-ink;
  font-size: 13px;
  font-weight: 600;
  padding: 10px 0;
  border-radius: 9999px;

  &--disabled {
    opacity: 0.5;
  }
}

.trim-undo {
  flex-shrink: 0;
  background-color: var(--color-page-bg, #F2F2EF);
  color: $color-olive-light;
  font-size: 13px;
  padding: 10px 18px;
  border-radius: 9999px;
}

.seg-list {
  margin-top: $space-sm;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.seg-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  background-color: rgba(var(--color-accent-rgb, 200, 218, 43), 0.28);
  border-radius: 8px;
  padding: 4px 8px;
}

.seg-chip-label {
  font-size: 11px;
  font-weight: 700;
  color: $color-ink;
}

.seg-chip-time {
  font-size: 11px;
  color: $color-olive-light;
  font-variant-numeric: tabular-nums;
}

.seg-chip-del {
  font-size: 12px;
  color: #c0392b;
  padding: 0 2px;
}

.seg-total {
  font-size: 11px;
  color: $color-olive-light;
  font-variant-numeric: tabular-nums;
}

.trim-warn {
  display: block;
  margin-top: 8px;
  font-size: 12px;
  color: #c0392b;
}

.trim-need {
  display: block;
  margin-top: 8px;
  font-size: 12px;
  color: $color-olive-light;
}

// ========== 分析按钮 ==========
.analyze-btn {
  background-color: var(--color-accent, #C8DA2B);
  color: $color-ink;
  text-align: center;
  font-size: 16px;
  font-weight: 600;
  padding: 14px 0;
  border-radius: 9999px;
  box-shadow: 0 4px 12px rgba(var(--color-accent-rgb, 200, 218, 43), 0.35);

  &--disabled {
    opacity: 0.6;
  }
}

.analyze-progress {
  display: block;
  text-align: center;
  font-size: 12px;
  color: $color-olive-light;
  margin-top: $space-sm;
}
</style>