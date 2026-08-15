<template>
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
            ? "上传包含一次完整挥拍的视频，播放到「击球瞬间」暂停，再点开始分析"
            : "上传 15-60 秒的训练/对拉片段，将综合分析动作、节奏与战术" }}
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
          <text class="upload-sub">支持 mp4 / mov，单次挥拍最长 15 秒 · 综合分析最长 60 秒</text>
        </view>
        <view v-else class="video-box">
          <video
            id="swingVideo"
            class="video-el"
            :src="videoPath"
            controls
            @pause="captureHitTime"
            @timeupdate="captureHitTime"
          />
          <view v-if="mode === 'single'" class="hit-row">
            <view class="hit-info">
              <text class="hit-label">击球瞬间</text>
              <text class="hit-value">{{ hitTimeText }}</text>
            </view>
            <view class="hit-btn press-btn" @tap="captureHitTime">设为击球瞬间</view>
          </view>
          <text class="video-sub">
            {{ mode === "single" ? "⏸ 拖动进度条，把画面停在你「击球的瞬间」" : "已选择视频，可直接开始分析" }}
          </text>
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
import { computed, ref } from "vue";

import Seg from "@/components/Seg.vue";
import {
  analyzePose,
  analyzeSwing,
  createAnalysis,
  uploadVideo,
} from "@/services/data";
import type { AnalysisKind, AnalysisPose, AnalysisReport } from "@/types";
import { ANALYSIS_KINDS, todayStr } from "@/utils";

type Mode = "single" | "full";

const mode = ref<Mode>("single");
const kind = ref<AnalysisKind>("正手");
const videoPath = ref("");
const analyzing = ref(false);
const progress = ref("");
const hitTime = ref(0);

const kindOptions = computed(() =>
  mode.value === "full"
    ? ANALYSIS_KINDS
    : (ANALYSIS_KINDS.filter((k) => k !== "综合") as readonly string[]),
);

const hitTimeText = computed(() =>
  hitTime.value > 0 ? `${hitTime.value.toFixed(1)}s` : "未设置（默认为视频中点）",
);

let videoCtx: UniApp.VideoContext | null = null;

function setMode(m: Mode) {
  mode.value = m;
  if (m === "full") {
    hitTime.value = 0;
  }
}

function chooseVideo() {
  uni.chooseVideo({
    sourceType: ["album", "camera"],
    maxDuration: 60,
    success: (res) => {
      videoPath.value = res.tempFilePath;
      hitTime.value = 0;
    },
    fail: (err) => {
      console.error("[chooseVideo] 失败", err);
      if (err.errMsg && !err.errMsg.includes("cancel")) {
        uni.showToast({ title: "选择视频失败，请检查权限设置", icon: "none" });
      }
    },
  });
}

/** 记录当前播放位置为击球瞬间（single 模式用，来自 video timeupdate/pause 事件） */
function captureHitTime(e: any) {
  if (mode.value !== "single") return;
  const t = e?.detail?.currentTime;
  if (typeof t === "number" && t > 0) {
    hitTime.value = t;
  }
}

async function startAnalysis() {
  if (analyzing.value || !videoPath.value) return;
  analyzing.value = true;
  try {
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

    // 1. 上传 + 抽帧（75-2）
    progress.value = "上传视频并抽取关键帧…";
    const uploaded = await uploadVideo(videoPath.value, {
      mode: mode.value,
      kind: kind.value,
      hit_time: mode.value === "single" && hitTime.value > 0 ? String(hitTime.value) : "",
    });

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
  } catch (e) {
    const msg = e instanceof Error ? e.message : "分析失败，请重试";
    uni.showToast({ title: msg, icon: "none" });
  } finally {
    analyzing.value = false;
    progress.value = "";
  }
}
</script>

<style scoped lang="scss">
.analyze-page {
  min-height: 100vh;
  background-color: $color-paper;
}

.analyze-body {
  padding: $space-lg;
  padding-top: $space-xl;
  display: flex;
  flex-direction: column;
  gap: $space-md;
}

.form-card {
  background-color: $color-white;
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
  background-color: $color-lime;
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
    background-color: $color-paper;
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
  background-color: $color-lime;
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

// ========== 分析按钮 ==========
.analyze-btn {
  background-color: $color-lime;
  color: $color-ink;
  text-align: center;
  font-size: 16px;
  font-weight: 600;
  padding: 14px 0;
  border-radius: 9999px;
  box-shadow: 0 4px 12px rgba(200, 218, 43, 0.35);

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