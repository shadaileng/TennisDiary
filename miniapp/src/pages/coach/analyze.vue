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
            :class="{ 'video-el--hidden': analyzing }"
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
              </view>

              <!-- 开放起点标记（在容器级别，不受轨道 transform 影响） -->
              <view
                v-if="pendingStart !== null"
                class="tl-pending-mark"
                :style="{ left: containerX(pendingStart) + 'px' }"
              >
                <view class="tl-pending-arrow"></view>
                <view class="tl-pending-line"></view>
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
        @tap="handleStartAnalysis"
      >
        <text v-if="analyzing">分析中，请稍候…</text>
        <text v-else>开始分析</text>
      </view>
    </view>

    <!-- ④ 全屏模态进度（上传/分析期间居中显示，阻断误操作） -->
    <view v-if="analyzing" class="progress-mask" @touchmove.stop.prevent @tap.stop>
      <view class="progress-card">
        <view class="progress-spinner" />
        <text class="progress-title">{{ progressTitle }}</text>
        <text class="progress-pct">{{ displayPercent }}%</text>
        <view class="progress-track">
          <view class="progress-bar" :style="{ width: displayPercent + '%' }" />
        </view>
        <text class="progress-desc">{{ progress }}</text>
        <view v-if="analysisStage === 'upload'" class="progress-cancel press-btn" @tap="cancelUpload">
          <text>{{ canceling ? "取消中…" : "取消上传" }}</text>
        </view>
        <text v-else class="progress-tip">分析约需 30~60 秒，请勿退出页面</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { onUnload } from "@dcloudio/uni-app";

import Seg from "@/components/Seg.vue";
import { useThemeStyle } from "@/composables/useTheme";
import { createStatusSubscriber, stepLabel, type AnalysisStatus } from "@/services/analysisStatus";
import { startAnalysis } from "@/services/data";
import type { AnalysisKind } from "@/types";
import { ANALYSIS_KINDS, todayStr } from "@/utils";
import { createTraceId, logError, logInfo } from "@/utils/eventLogger";
import { isUserCancel, isRuntimePermissionDenied, isPrivacyScopeError } from "@/utils/privacy";
import {
  checkFile,
  getFileFingerprint,
  resolveUploadTimeout,
  uploadRaw,
  FINGERPRINT_MAX_SIZE,
  type FileFingerprint,
} from "@/utils/upload";

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
/** 上传进度百分比（137 加固：上传期间给用户明确反馈） */
const uploadPercent = ref(0);
/** 当前阶段：upload=取文件/上传，analyze=后台管线分析（驱动模态进度展示） */
const analysisStage = ref<"" | "upload" | "analyze">("");
/** 上传已传/总字节数（模态副文本展示） */
const uploadSent = ref(0);
const uploadTotal = ref(0);
/** 已选视频的文件指纹（选后异步预计算，供秒传预检使用） */
const videoFingerprint = ref<FileFingerprint | null>(null);
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

// ============ 状态订阅（119：混合模式） ============
let statusSubscriber: { start: () => void; stop: () => void } | null = null;
const pipelineStep = ref("");
const pipelineProgress = ref(0);

// ============ 模态进度（上传/分析） ============
/** 上传任务句柄：供「取消上传」中断 */
let uploadTask: UniApp.UploadTask | null = null;
/** 是否由用户主动取消（取消后不再弹失败提示） */
let uploadCanceled = false;
/** 取消中（预检阶段无任务可 abort，等待流程到达检查点） */
const canceling = ref(false);
/** 当前链路 trace_id，供取消埋点串联 */
let currentTraceId = "";

/** 模态百分比：上传取上传进度，分析取管线进度 */
const displayPercent = computed(() => {
  const raw = analysisStage.value === "upload" ? uploadPercent.value : pipelineProgress.value;
  return Math.min(Math.max(Math.round(Number(raw) || 0), 0), 100);
});

const progressTitle = computed(() =>
  analysisStage.value === "upload" ? "正在上传视频" : "AI 分析进行中",
);

function fmtSize(bytes: number): string {
  const mb = (Number(bytes) || 0) / 1024 / 1024;
  return `${mb.toFixed(1)}MB`;
}

/** 收尾：关闭模态并清空进度状态 */
function resetProgressState() {
  analyzing.value = false;
  analysisStage.value = "";
  uploadTask = null;
  canceling.value = false;
  uploadSent.value = 0;
  uploadTotal.value = 0;
  progress.value = "";
  uploadPercent.value = 0;
  stopStatusSubscriber();
}

/** 取消当前上传（分析阶段不提供取消，避免产生孤儿分析记录） */
function cancelUpload() {
  if (uploadCanceled) return;
  const task = uploadTask;
  uploadCanceled = true;

  // 指纹/秒传预检阶段尚无上传任务：标记取消，流程在下一个检查点中断
  if (!task) {
    canceling.value = true;
    logInfo("取消分析（预检阶段）", { trace_id: currentTraceId }, undefined, "video_upload_canceled", currentTraceId);
    uni.showToast({ title: "正在取消…", icon: "none" });
    return;
  }

  uploadTask = null;
  logInfo("取消视频上传", { trace_id: currentTraceId }, undefined, "video_upload_canceled", currentTraceId);
  task.abort();
  uni.showToast({ title: "已取消上传", icon: "none" });
  // 兜底：个别基础库 abort 不回调，避免模态卡死
  setTimeout(() => {
    if (!uploadCanceled || !analyzing.value) return;
    resetProgressState();
    uploadCanceled = false;
  }, 1500);
}

/** 停止状态订阅 */
function stopStatusSubscriber() {
  if (statusSubscriber) {
    statusSubscriber.stop();
    statusSubscriber = null;
  }
}

/** 页面卸载时清理

 * 注意：必须用 uni-app 的 `onUnload`（页面生命周期），不能用 Vue 的 `onUnmounted`——
 * 小程序页面由原生页面栈管理，navigateBack 销毁页面时 `onUnmounted` 不保证触发，
 * 会导致 status 订阅泄漏、离开页面后仍持续轮询（139 §2.6）。
 *
 * 此处**不要**额外加 `onHide` 停止订阅：该订阅服务于 startAnalysis 的 Promise，
 * 页面隐藏即停会导致 Promise 永不 resolve（139 决策 12）。
 */
onUnload(() => {
  stopStatusSubscriber();
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
  logInfo("选择视频", { trace_id: traceId }, undefined, "choose_video", traceId);

  // 已使用 chooseMedia 替代已废弃的 chooseVideo，无需超时兜底；
  // 大视频在系统相册选择/压缩时可能耗时较长，固定超时会导致误报。
  let finished = false;

  uni.chooseMedia({
    count: 1,
    mediaType: ["video"],
    sourceType: ["album", "camera"],
    success: (res) => {
      if (finished) return;
      finished = true;

      const file = res.tempFiles?.[0];
      if (!file || !file.tempFilePath) {
        logError("选择视频返回为空", { trace_id: traceId }, undefined, "choose_video_empty", undefined, traceId);
        uni.showToast({ title: "选择视频失败，请重试", icon: "none" });
        return;
      }

      const dur = Number(file.duration) || 0;
      if (dur > UPLOAD_MAX) {
        uni.showToast({ title: `视频 ${Math.round(dur)}s 超过 3 分钟，请先在相册裁剪`, icon: "none" });
        logInfo("视频超长被拒", { trace_id: traceId, duration: dur }, undefined, "choose_video_too_long", traceId);
        return;
      }
      videoPath.value = file.tempFilePath;
      videoDuration.value = dur;
      hitTime.value = 0;
      videoFingerprint.value = null;
      resetSegments();
      playhead.value = 0;
      pps.value = TRACK_PPS;
      zoomInitialized = false;
      measureBar();
      logInfo("视频选择成功", { trace_id: traceId, duration: dur }, undefined, "choose_video_success", traceId);

      // 异步预计算指纹（与剪辑/设置击球点并行，不在关键路径）
      precomputeFingerprint(file.tempFilePath, Number(file.size) || 0, traceId);
    },
    fail: (err) => {
      if (finished) return;
      finished = true;

      if (isUserCancel(err)) {
        logInfo("用户取消选择视频", { trace_id: traceId }, undefined, "choose_video_cancel", traceId);
      } else if (isRuntimePermissionDenied(err)) {
        logError("选择视频权限被拒绝", { trace_id: traceId, error: err.errMsg }, undefined, "choose_video_denied", undefined, traceId);
        uni.showToast({ title: "需要授权使用相册/相机功能", icon: "none" });
      } else if (isPrivacyScopeError(err)) {
        logError("隐私声明未配置", { trace_id: traceId, error: err.errMsg }, undefined, "choose_video_privacy", undefined, traceId);
        uni.showToast({ title: "隐私权限未配置，请联系开发者", icon: "none" });
      } else {
        logError("选择视频失败", { trace_id: traceId, error: err.errMsg }, undefined, "choose_video_failed", undefined, traceId);
        uni.showToast({ title: "选择视频失败，请重试", icon: "none" });
      }
    },
    complete: () => {
      finished = true;
    },
  });
}

/**
 * 选择视频后异步预计算指纹（MD5 + size）
 *
 * 超大文件直接跳过（计算耗时不可接受）；失败静默，仅失去秒传机会，
 * 点击分析时会再兜底算一次。
 */
function precomputeFingerprint(path: string, size: number, traceId: string) {
  if (size && size > FINGERPRINT_MAX_SIZE) {
    logInfo("视频过大跳过指纹预计算", { trace_id: traceId, size }, undefined, "video_fingerprint_skipped", traceId);
    return;
  }
  void getFileFingerprint(path)
    .then((fp) => {
      // 期间用户可能换了视频，按路径校验后写入
      if (videoPath.value !== path) return;
      videoFingerprint.value = fp;
      logInfo(
        "视频指纹预计算完成",
        { trace_id: traceId, size: fp.size, duration_ms: fp.durationMs },
        undefined,
        "video_fingerprint_ready",
        traceId,
      );
    })
    .catch(() => {
      logInfo("视频指纹预计算失败，退回整体上传", { trace_id: traceId }, undefined, "video_fingerprint_failed", traceId);
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

/** 弱网/离线提示（上传前一次性提醒，不阻断流程） */
function warnWeakNetwork(traceId: string): Promise<void> {
  return new Promise((resolve) => {
    uni.getNetworkType({
      success: (res: any) => {
        const type = (res?.networkType as string) || "";
        if (type === "none") {
          logError("上传前检测到无网络", { trace_id: traceId }, undefined, "video_upload_offline", undefined, traceId);
          uni.showToast({ title: "当前无网络，请检查后重试", icon: "none" });
        } else if (type === "2g" || type === "3g") {
          logInfo("上传前检测到弱网", { trace_id: traceId, network_type: type }, undefined, "video_upload_weak_network", traceId);
          uni.showToast({ title: "当前网络较慢，上传可能需要较长时间", icon: "none" });
        }
        resolve();
      },
      fail: () => resolve(),
    });
  });
}

/**
 * 解析出可用于启动分析的 file_id（137 两步秒传）
 *
 * 1）优先按 MD5 预检（命中 → 零流量，秒传成功）
 * 2）未命中 → 整体上传 /upload/video（超时按体积自适应）
 * 3）预检失败/指纹不可用 → 静默退回上传，流程不中断
 */
async function resolveVideoFileId(traceId: string): Promise<number> {
  const path = videoPath.value;

  // 1. 指纹（优先复用选视频后的预计算结果）
  let fp = videoFingerprint.value;
  if (!fp) {
    try {
      fp = await getFileFingerprint(path);
      videoFingerprint.value = fp;
    } catch {
      logInfo("指纹计算失败，直接上传", { trace_id: traceId }, undefined, "video_fingerprint_failed", traceId);
    }
  }

  // 2. 秒传预检（按 video 来源隔离）
  if (fp?.md5) {
    try {
      const check = await checkFile(fp.md5, fp.size, "video");
      if (check.hit && check.safe && check.file_id) {
        logInfo(
          "视频秒传命中",
          { trace_id: traceId, file_id: check.file_id, size: fp.size },
          undefined,
          "video_upload_mirage",
          traceId,
        );
        return check.file_id;
      }
      logInfo("视频预检未命中", { trace_id: traceId, hit: check.hit }, undefined, "video_check_miss", traceId);
    } catch {
      logInfo("视频预检失败，退回上传", { trace_id: traceId }, undefined, "video_check_failed", traceId);
    }
  }

  // 3. 整体上传
  await warnWeakNetwork(traceId);
  uploadPercent.value = 0;
  const res = await uploadRaw<{ file_id?: number; mirage?: boolean }>({
    path: "/upload/video",
    filePath: path,
    fieldName: "file",
    timeout: resolveUploadTimeout(fp?.size || 0),
    onTask: (task) => {
      uploadTask = task;
      // 预检阶段已点取消：上传任务一创建立即中断，避免白耗流量
      if (uploadCanceled) {
        uploadTask = null;
        task.abort();
      }
    },
    onProgress: (p) => {
      uploadPercent.value = Math.min(Math.round(p.percent || 0), 100);
      uploadSent.value = Number(p.transferred) || 0;
      uploadTotal.value = Number(p.total) || 0;
      progress.value = `已传 ${fmtSize(uploadSent.value)} / ${fmtSize(uploadTotal.value)}`;
    },
    onSuccess: (_result, durationMs) => {
      uploadTask = null;
      uploadPercent.value = 100;
      logInfo(
        "视频上传成功",
        { trace_id: traceId, duration_ms: durationMs, size: fp?.size || 0 },
        undefined,
        "video_upload_success",
        traceId,
      );
    },
    onMirage: (_result, durationMs) => {
      uploadTask = null;
      uploadPercent.value = 100;
      logInfo(
        "视频上传命中秒传",
        { trace_id: traceId, duration_ms: durationMs },
        undefined,
        "video_upload_mirage",
        traceId,
      );
    },
    onFailed: (error, durationMs) => {
      logError(
        "视频上传失败",
        { trace_id: traceId, duration_ms: durationMs, error: error.message, size: fp?.size || 0 },
        undefined,
        "video_upload_failed",
        undefined,
        traceId,
      );
    },
  });

  const fileId = Number(res.file_id) || 0;
  if (!fileId) {
    throw new Error("视频上传失败，请重试");
  }
  uploadPercent.value = 100;
  return fileId;
}

/**
 * 统一分析端点模式（119 + 137）
 * 前端先解析 file_id（秒传预检/整体上传），再凭 file_id 启动后台管线
 */
async function startAnalysisUnified() {
  if (analyzing.value || !videoPath.value) return;
  const traceId = createTraceId();
  currentTraceId = traceId;
  const t0 = Date.now();

  const dur = videoDuration.value;
  if (!trimmed.value) {
    if (dur <= 0) {
      uni.showToast({ title: "视频时长未加载，请稍候或重新选择视频后在时间轴截取片段", icon: "none" });
      return;
    }
    if (dur > modeLimit.value) {
      uni.showToast({ title: `视频超过 ${UPLOAD_MAX} 秒上限，请先在相册裁剪后再上传`, icon: "none" });
      return;
    }
  }

  analyzing.value = true;
  analysisStage.value = "upload";
  uploadCanceled = false;
  canceling.value = false;
  // 视频为原生组件（层级最高），进入模态前暂停并隐藏，避免遮挡进度弹层
  videoCtx?.pause();
  isPlaying.value = false;
  let analysisId = 0;
  try {
    // 0. 检查视频文件是否存在
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

    // === 整体入口 ===
    logInfo("开始AI分析（统一端点）", {
      trace_id: traceId, mode: mode.value, kind: kind.value,
      has_cuts: trimmed.value, video_duration: videoDuration.value,
      segment_count: segments.value.length,
    }, undefined, "analysis_started", traceId);

    // === 步骤1: 解析 file_id（秒传预检 / 整体上传） ===
    progress.value = "准备上传…";
    logInfo("统一分析开始", { trace_id: traceId }, undefined, "unified_analysis_start", traceId);
    const tStart = Date.now();

    const fileId = await resolveVideoFileId(traceId);
    // 取消检查点：预检/上传阶段被取消则不再启动分析
    if (uploadCanceled) throw new Error("已取消上传");

    // === 步骤2: 凭 file_id 启动后台分析管线 ===
    analysisStage.value = "analyze";
    progress.value = "启动分析…";
    const startRes = await startAnalysis({
      file_id: fileId,
      date: todayStr(),
      kind: kind.value,
      mode: mode.value,
      hit_time: mode.value === "single" && hitTime.value > 0 ? Number(hitTime.value.toFixed(2)) : 0,
      cuts: trimmed.value
        ? segments.value.map((s) => ({ start: round2(s.start), end: round2(s.end) }))
        : undefined,
    });

    analysisId = startRes.id;
    logInfo("统一分析已启动", {
      trace_id: traceId, duration_ms: Date.now() - tStart, analysis_id: analysisId, file_id: fileId,
    }, undefined, "unified_analysis_launched", traceId);

    // === 步骤3: 订阅状态更新 ===
    progress.value = "分析中，请稍候…";
    logInfo("状态订阅开始", { trace_id: traceId, analysis_id: analysisId }, undefined, "status_subscribe_start", traceId);

    await new Promise<void>((resolve, reject) => {
      statusSubscriber = createStatusSubscriber(analysisId, (status: AnalysisStatus) => {
        // 更新进度显示
        if (status.pipeline_status) {
          pipelineStep.value = status.pipeline_status.step;
          pipelineProgress.value = status.pipeline_status.progress;

          progress.value = stepLabel(status.pipeline_status.step);
        }

        // 完成时跳转报告页
        if (status.status === "completed") {
          logInfo("分析完成", {
            trace_id: traceId, analysis_id: analysisId,
            total_duration_ms: Date.now() - t0,
          }, undefined, "analysis_completed", traceId);
          stopStatusSubscriber();
          uni.redirectTo({ url: `/pages/coach/report?id=${analysisId}` });
          resolve();
        }

        // 失败时提示
        if (status.status === "failed") {
          const errorMsg = status.pipeline_status?.error || "分析失败，请重试";
          logError("分析失败", {
            trace_id: traceId, analysis_id: analysisId, error: errorMsg,
          }, undefined, "analysis_failed", undefined, traceId);
          stopStatusSubscriber();
          reject(new Error(errorMsg));
        }
      }, {
        // 139：订阅超时必须收尾。若不处理，轮询停止后 await 永不返回，
        // 模态会永久卡在"AI 分析进行中"（比修复前更糟）。
        // reject 后由下方 catch/finally 统一提示并关闭模态。
        onTimeout: () => {
          stopStatusSubscriber();
          logError("分析状态订阅超时", {
            trace_id: traceId, analysis_id: analysisId,
            total_duration_ms: Date.now() - t0,
          }, undefined, "analysis_subscribe_timeout", traceId);
          reject(new Error("分析超时，请稍后到列表查看结果"));
        },
      });

      statusSubscriber.start();
    });
  } catch (e) {
    const msg = e instanceof Error ? e.message : "分析失败，请重试";
    // 用户主动取消：已单独提示，不再弹失败文案
    if (uploadCanceled) return;
    logError("统一分析失败", {
      trace_id: traceId, error: msg,
      mode: mode.value, kind: kind.value,
      total_duration_ms: Date.now() - t0,
    }, undefined, "analysis_failed", undefined, traceId);
    // 文件失效（file_id 指向的物理文件已不在）：清掉指纹，重试时会重新上传
    if (msg.includes("失效") || msg.includes("不存在")) {
      videoFingerprint.value = null;
    }
    // 保留 videoPath：用户可直接点「开始分析」重试
    uni.showToast({ title: msg, icon: "none" });
  } finally {
    uploadCanceled = false;
    resetProgressState();
  }
}

/** 启动分析 */
function handleStartAnalysis() {
  startAnalysisUnified();
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

  // 模态进度期间隐藏：video 是原生组件层级最高，会盖住遮罩
  &--hidden {
    display: none;
  }
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
  width: 4px;
  transform: translateX(-2px);
  z-index: 11;
  display: flex;
  flex-direction: column;
  align-items: center;

  // 顶部箭头（指向下方）
  .tl-pending-arrow {
    position: absolute;
    top: 2px;
    left: 50%;
    transform: translateX(-50%);
    width: 0;
    height: 0;
    border-left: 8px solid transparent;
    border-right: 8px solid transparent;
    border-top: 10px solid var(--color-accent, #C8DA2B);
    filter: drop-shadow(0 1px 2px rgba(0, 0, 0, 0.3));
  }

  // 竖线（贯穿时间轴）
  .tl-pending-line {
    position: absolute;
    top: 10px;
    bottom: 0;
    left: 50%;
    width: 4px;
    margin-left: -2px;
    background: var(--color-accent, #C8DA2B);
    box-shadow: 0 0 4px rgba(200, 218, 43, 0.5);
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

// ========== 模态进度遮罩 ==========
.progress-mask {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: $space-xl;
  background-color: rgba(0, 0, 0, 0.55);
}

.progress-card {
  width: 100%;
  max-width: 300px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: $space-sm;
  padding: $space-xl $space-lg;
  background-color: $color-white;
  border-radius: $radius-card;
  box-shadow: $shadow-card-md;
}

.progress-spinner {
  width: 36px;
  height: 36px;
  border: 4px solid var(--color-accent-soft, $color-lime-soft);
  border-top-color: var(--color-accent-dark, $color-lime-dark);
  border-radius: 50%;
  animation: progress-spin 0.8s linear infinite;
}

.progress-title {
  font-size: $font-size-base;
  font-weight: 600;
  color: $color-ink;
}

.progress-pct {
  font-size: 30px;
  font-weight: 700;
  color: $color-ink;
  font-variant-numeric: tabular-nums;
  line-height: 1.1;
}

.progress-track {
  width: 100%;
  height: 8px;
  border-radius: 9999px;
  background-color: var(--color-accent-soft, $color-lime-soft);
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  border-radius: 9999px;
  background-color: var(--color-accent, #C8DA2B);
  transition: width 0.3s ease;
}

.progress-desc {
  display: block;
  font-size: $font-size-sm;
  color: $color-olive-light;
  text-align: center;
}

.progress-tip {
  display: block;
  margin-top: $space-xs;
  font-size: 12px;
  color: $color-olive-light;
  text-align: center;
}

.progress-cancel {
  margin-top: $space-sm;
  padding: 8px 24px;
  border-radius: 9999px;
  background-color: var(--color-page-bg, #F2F2EF);
  font-size: $font-size-sm;
  color: $color-olive-light;
}

@keyframes progress-spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>