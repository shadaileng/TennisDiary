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
            @pause="isPlaying = false; captureHitTime($event)"
            @timeupdate="captureHitTime"
          />
          <view v-if="mode === 'single'" class="hit-row">
            <view class="hit-info">
              <text class="hit-label">击球瞬间（片段内）</text>
              <text class="hit-value">{{ hitTimeText }}</text>
            </view>
            <view class="hit-btn press-btn" @tap="captureHitTime">设为击球瞬间</view>
          </view>
          <text class="video-sub">
            {{ mode === "single" ? "🧭 用下方时间轴拖动播放头到击球瞬间，或视频内直接暂停定位" : "🧭 可在下方时间轴添加多个片段拼接分析" }}
          </text>

          <!-- 时间轴剪辑 -->
          <view v-if="videoDuration > 0" class="trim-section">
            <view class="trim-head">
              <text class="trim-title">时间轴剪辑</text>
              <text class="trim-meta">{{ trimMetaText }}</text>
            </view>

            <view
              class="timeline-bar"
              @touchstart="onBarTouchStart"
              @touchmove="onBarTouchMove"
              @touchend="onBarTouchEnd"
              @touchcancel="onBarTouchEnd"
            >
              <!-- 基线刻度 -->
              <view class="tl-track"></view>
              <!-- 片段色块：点击居中预览 -->
              <view
                v-for="(sg, i) in segments"
                :key="sg.key"
                class="tl-block"
                :style="blockStyle(sg)"
                @tap.stop="centerOnSegment(i)"
              >
                <text class="tl-block-label">{{ i + 1 }}</text>
              </view>
              <!-- 未闭合起点 -->
              <view
                v-if="pendingStart !== null"
                class="tl-start-mark"
                :style="markStyle(pendingStart)"
              >▶</view>
              <!-- 播放头 -->
              <view class="tl-playhead" :style="playheadStyle"></view>
            </view>

            <view class="timeline-info">
              <text class="tl-info-time">▶ {{ fmtTime(playhead) }}s / {{ fmtTime(videoDuration) }}s</text>
              <text class="tl-info-zoom">视野 {{ fmtTime(visibleSpan) }}s · 双指缩放 · 上拖播放头 / 下拖平移</text>
            </view>

            <view class="trim-actions">
              <view
                class="trim-btn press-btn"
                :class="{ 'trim-btn--disabled': !canAddSegment && pendingStart === null }"
                @tap="toggleSegment"
              >
                {{ pendingStart === null ? "➕ 起点" : "✋ 终点" }} @ {{ fmtTime(playhead) }}s
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
import { computed, nextTick, onMounted, ref } from "vue";

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

// 与后端 video_service 对齐的裁剪约束
const UPLOAD_MAX = 180;
const MODE_LIMIT: Record<Mode, number> = { single: 15, full: 90 };
const MAX_SEGMENTS: Record<Mode, number> = { single: 1, full: 8 };
const MIN_SEGMENT = 0.6;
const MIN_ZOOM_SPAN = 2;

const mode = ref<Mode>("single");
const kind = ref<AnalysisKind>("正手");
const videoPath = ref("");
const videoDuration = ref(0);
const analyzing = ref(false);
const progress = ref("");
const hitTime = ref(0);
const warnMsg = ref("");
const videoReady = ref(false); // 视频元数据就绪（可安全 seek 预览）
const isPlaying = ref(false); // 视频播放态（决定拖动时是否需要强制刷新帧）

// ============ 时间轴状态 ============
const segments = ref<TrimSegment[]>([]);
const pendingStart = ref<number | null>(null);
const playhead = ref(0);
const visibleSpan = ref(0); // 可见时间窗（秒）
const viewStart = ref(0); // 可见窗左边界（原始时间轴秒）
const barWidth = ref(0);
const barLeft = ref(0);
const barTop = ref(0);
const barHeight = ref(44);
let segKey = 0;

let videoCtx: UniApp.VideoContext | null = null;
let dragMode: "none" | "scrub" | "pan" | "pinch" = "none";
let pinchDist = 0;
let lastPanX = 0;
let lastSeekTs = 0;

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
const canAddSegment = computed(() => {
  if (pendingStart.value !== null) return true;
  const lastEnd = segments.value.length
    ? segments.value[segments.value.length - 1].end
    : 0;
  return (
    segments.value.length < MAX_SEGMENTS[mode.value] &&
    playhead.value > lastEnd + 0.01 &&
    videoDuration.value > 0
  );
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
      visibleSpan.value = dur || 60;
      viewStart.value = 0;
      playhead.value = 0;
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
    visibleSpan.value = d;
  }
  // 视频元素此时已渲染，重新绑定上下文保证 seek 预览可用
  videoCtx = uni.createVideoContext("swingVideo");
  videoReady.value = true;
}

// ============ 时间轴坐标换算 ============
function measureBar() {
  nextTick(() => {
    uni.createSelectorQuery()
      .select(".timeline-bar")
      .boundingClientRect((rect: any) => {
        if (rect && rect.width > 0) {
          barWidth.value = rect.width;
          barLeft.value = rect.left;
          barTop.value = rect.top;
          if (rect.height > 0) barHeight.value = rect.height;
        }
      })
      .exec();
  });
}

function t2x(t: number): number {
  if (!barWidth.value || !visibleSpan.value) return 0;
  return ((t - viewStart.value) / visibleSpan.value) * barWidth.value;
}

function x2t(x: number): number {
  if (!barWidth.value || !visibleSpan.value) return 0;
  return viewStart.value + (x / barWidth.value) * visibleSpan.value;
}

function clampT(t: number): number {
  const dur = videoDuration.value;
  return Math.min(Math.max(0, t), Math.max(0, dur));
}

/** 把可见窗左边界夹紧到 [0, duration - visibleSpan]，全览时归 0 */
function clampViewStart(vs: number): number {
  const dur = videoDuration.value;
  const span = visibleSpan.value;
  if (span >= dur - 0.01) return 0;
  return Math.min(Math.max(0, vs), Math.max(0, dur - span));
}

/** 点击选中的片段 → 视野居中该片段并预览中点帧 */
function centerOnSegment(i: number) {
  const sg = segments.value[i];
  if (!sg) return;
  const mid = (sg.start + sg.end) / 2;
  playhead.value = mid;
  viewStart.value = clampViewStart(mid - visibleSpan.value / 2);
  flushPlayhead();
}

// ============ 时间轴手势：纵向分区（上拖播放头 scrub / 下拖平移 pan）+ 双指捏合缩放 ============
function resolveModeByY(touch: any): "scrub" | "pan" {
  const y = touch.clientY - barTop.value;
  return y < barHeight.value / 2 ? "scrub" : "pan";
}

function onBarTouchStart(e: any) {
  const touches = e.touches || [];
  if (touches.length >= 2) {
    dragMode = "pinch";
    pinchDist = touchDist(touches);
    return;
  }
  dragMode = touches[0] ? resolveModeByY(touches[0]) : "scrub";
  lastPanX = touches[0]?.clientX ?? 0;
}

function onBarTouchMove(e: any) {
  const touches = e.touches || [];
  if (touches.length >= 2) {
    if (dragMode === "none" || dragMode === "pan" || dragMode === "scrub") dragMode = "pinch";
    if (dragMode === "pinch") {
      const d = touchDist(touches);
      if (pinchDist <= 0) pinchDist = d;
      applyPinch(d);
    }
  } else if (touches.length === 1) {
    if (dragMode === "pinch") dragMode = resolveModeByY(touches[0]); // 抬指从捏合切回，按剩余手指 y 重新分区
    if (dragMode === "scrub") {
      const t = clampT(x2t(touches[0].clientX - barLeft.value));
      playhead.value = t;
      throttleSeek(t);
      keepInView();
    } else if (dragMode === "pan") {
      const x = touches[0].clientX;
      const dx = x - lastPanX;
      if (dx !== 0) {
        const dt = (dx / barWidth.value) * visibleSpan.value;
        viewStart.value = clampViewStart(viewStart.value - dt);
        lastPanX = x;
      }
    }
  }
}

function onBarTouchEnd() {
  const wasScrub = dragMode === "scrub";
  dragMode = "none";
  pinchDist = 0;
  if (wasScrub) flushPlayhead(); // 松手补帧：节流可能跳过最后一帧；平移结束不跳帧
}

function touchDist(touches: any[]): number {
  const a = touches[0];
  const b = touches[1];
  if (!a || !b) return 0;
  return Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY);
}

function applyPinch(dist: number) {
  if (!barWidth.value || dist <= 0 || pinchDist <= 0) return;
  const dur = videoDuration.value;
  const anchorX = t2x(playhead.value);
  const factor = pinchDist / dist; // 手指张开 → 放大（视野变窄）
  const newSpan = Math.min(Math.max(visibleSpan.value * factor, MIN_ZOOM_SPAN), dur);
  const ratio = barWidth.value ? anchorX / barWidth.value : 0.5;
  visibleSpan.value = newSpan;
  viewStart.value = clampViewStart(playhead.value - ratio * newSpan);
  pinchDist = dist;
}

function keepInView() {
  const dur = videoDuration.value;
  const span = visibleSpan.value;
  if (span >= dur - 0.01) {
    viewStart.value = 0;
    return;
  }
  const p = playhead.value;
  let vs = viewStart.value;
  if (p < vs + span * 0.1) vs = p - span * 0.1;
  else if (p > vs + span * 0.9) vs = p - span * 0.9;
  viewStart.value = clampViewStart(vs);
}

function throttleSeek(t: number) {
  const now = Date.now();
  if (now - lastSeekTs < 50) return;
  lastSeekTs = now;
  seekPreview(t);
}

/** seek + （暂停态下）play/pause 强制刷新目标帧（Chromium 模拟器/真机通用） */
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

/** 松手/设点后强制刷新一次目标帧（节流可能跳过最后一帧） */
function flushPlayhead() {
  seekPreview(playhead.value);
}

// ============ 片段（起始点/结束点） ============
function toggleSegment() {
  const t = playhead.value;
  if (pendingStart.value === null) {
    if (!canAddSegment.value) {
      warnMsg.value =
        segments.value.length >= MAX_SEGMENTS[mode.value]
          ? `${mode.value === "full" ? "最多 8" : "最多 1"} 段，先点击已选片段删除`
          : "起点需晚于上一段终点";
      return;
    }
    pendingStart.value = t;
    warnMsg.value = "";
    throttleSeek(t);
  } else {
    const start = pendingStart.value;
    const end = t;
    if (end - start < MIN_SEGMENT) {
      warnMsg.value = "片段最短 0.6 秒";
      return;
    }
    const extra = end - start;
    if (totalConcat.value + extra > modeLimit.value + 0.001) {
      warnMsg.value = `片段总长超上限 ${modeLimit.value}s（当前 ${(totalConcat.value + extra).toFixed(1)}s），请缩短终点`;
      return;
    }
    segments.value.push({ key: segKey++, start, end });
    pendingStart.value = null;
    warnMsg.value = "";
  }
}

function removeSegment(i: number) {
  segments.value.splice(i, 1);
  warnMsg.value = "";
}

function resetSegments() {
  segments.value = [];
  pendingStart.value = null;
  warnMsg.value = "";
}

// ============ 样式（坐标转 px） ============
function blockStyle(sg: TrimSegment) {
  const left = t2x(sg.start);
  const width = t2x(sg.end) - left;
  return { left: `${left}px`, width: `${width}px` };
}

function markStyle(t: number) {
  return { left: `${t2x(t)}px` };
}

function playheadStyle() {
  const x = t2x(playhead.value);
  return { left: `${x}px` };
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

function captureHitTime(e: any) {
  if (mode.value !== "single") return;
  const t = e?.detail?.currentTime;
  if (typeof t !== "number" || t <= 0) return;
  if (segmentIndexAt(t) < 0) {
    warnMsg.value = trimmed.value ? "击球瞬间需落在所选片段内" : "";
    return;
  }
  const concatT = toConcatTime(t);
  if (concatT === null) return;
  hitTime.value = concatT;
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
      uni.showToast({ title: `请先在时间轴裁剪片段（裁剪后总长 ≤ ${modeLimit.value}s）`, icon: "none" });
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

.timeline-bar {
  position: relative;
  height: 44px;
  border-radius: 8px;
  background-color: var(--color-page-bg, #F2F2EF);
  overflow: hidden;
}

.tl-track {
  position: absolute;
  top: 50%;
  left: 0;
  right: 0;
  height: 6px;
  transform: translateY(-50%);
  border-radius: 3px;
  background: linear-gradient(90deg, #d8d8d0, #c8c8c0 50%, #d8d8d0);
}

.tl-block {
  position: absolute;
  top: 7px;
  bottom: 7px;
  border-radius: 6px;
  background: rgba(var(--color-accent-rgb, 200, 218, 43), 0.55);
  border: 1px solid var(--color-accent-dark, #A8B822);
  display: flex;
  align-items: center;
  justify-content: flex-start;
  padding-left: 4px;
  box-sizing: border-box;
}

.tl-block-label {
  font-size: 10px;
  font-weight: 700;
  color: $color-ink;
}

.tl-start-mark {
  position: absolute;
  top: 0;
  width: 0;
  height: 0;
  border-left: 7px solid var(--color-accent, #C8DA2B);
  border-top: 6px solid transparent;
  border-bottom: 6px solid transparent;
  transform: translateX(-50%);
}

.tl-playhead {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 2px;
  background: var(--color-accent-dark, #A8B822);
  transform: translateX(-1px);

  &::before {
    content: "";
    position: absolute;
    top: -2px;
    left: -4px;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: var(--color-accent, #C8DA2B);
    border: 2px solid $color-white;
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