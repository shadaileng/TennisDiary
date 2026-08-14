<template>
  <view class="report-page">
    <view v-if="!analysis" class="report-loading">
      <text>加载中…</text>
    </view>

    <view v-else class="report-body">
      <!-- 封面 + 评分圆徽 -->
      <view class="cover-wrap">
        <image v-if="coverSrc" :src="coverSrc" mode="aspectFill" class="cover-img" />
        <view v-else class="cover-placeholder">🎾</view>
        <view v-if="(analysis.score || 0) > 0" class="score-badge">
          <text class="score-badge-value">{{ analysis.score }}</text>
          <text class="score-badge-label">SCORE</text>
        </view>
        <text v-if="pose?.detected" class="skeleton-badge">🦴 骨架标注</text>
      </view>

      <!-- 摘要 -->
      <view class="summary-block">
        <view class="summary-tags">
          <text class="tag-kind">{{ analysis.kind }}</text>
          <text v-if="analysis.ntrp" class="tag-ntrp">NTRP {{ analysis.ntrp }}</text>
          <text class="tag-mode">{{ analysis.mode === "single" ? "单次挥拍分析" : "综合分析" }} · {{ analysis.date }}</text>
        </view>
        <text class="summary-text">{{ analysis.summary }}</text>
        <text v-if="analysis.ntrp" class="ntrp-note">NTRP 为 AI 基于本段视频的参考评估，仅供对照成长，非官方定级</text>
      </view>

      <!-- 六维评分：雷达图 + 逐项点评 -->
      <view v-if="report && report.dimensions && report.dimensions.length > 0" class="form-card">
        <text class="card-title">📐 分维度点评</text>
        <RadarChart v-if="report.dimensions.length >= 3" :data="report.dimensions" class="radar-chart" />
        <view v-for="d in report.dimensions" :key="d.name" class="dim-item">
          <view class="dim-head">
            <text class="dim-name">{{ d.name }}</text>
            <text class="dim-score">{{ d.score }}</text>
          </view>
          <view class="dim-bar">
            <view class="dim-bar-fill" :style="{ width: dimWidth(d.score) }" />
          </view>
          <text class="dim-comment">{{ d.comment }}</text>
        </view>
      </view>

      <!-- 姿态测量 + 视频回看（Step 83） -->
      <view v-if="pose?.detected || analysis.video_url" class="form-card">
        <text class="card-title">🦴 姿态测量</text>
        <view v-if="pose?.detected && pose.metrics" class="pose-metrics">
          <view class="pose-metric">
            <text class="pose-metric-value">{{ Math.round(pose.metrics.elbowAngle) }}°</text>
            <text class="pose-metric-label">肘角</text>
          </view>
          <view class="pose-metric">
            <text class="pose-metric-value">{{ Math.round(pose.metrics.kneeAngle) }}°</text>
            <text class="pose-metric-label">膝角</text>
          </view>
          <view class="pose-metric">
            <text class="pose-metric-value">{{ Math.round(pose.metrics.trunkLean) }}°</text>
            <text class="pose-metric-label">躯干倾斜</text>
          </view>
        </view>
        <text v-else class="pose-none">未检测到清晰的人体姿态，可查看原视频回放</text>

        <view v-if="skeletonVideoSrc || originalVideoSrc" class="pose-video">
          <view v-if="skeletonVideoSrc && originalVideoSrc" class="video-toggle">
            <view
              class="video-toggle-pill press-btn"
              :class="activeVideo === 'original' ? 'video-toggle-pill--active' : ''"
              @tap="activeVideo = 'original'"
            >原视频</view>
            <view
              class="video-toggle-pill press-btn"
              :class="activeVideo === 'skeleton' ? 'video-toggle-pill--active' : ''"
              @tap="activeVideo = 'skeleton'"
            >骨架视频</view>
          </view>
          <video
            v-if="activeVideoSrc"
            class="pose-video-el"
            :src="activeVideoSrc"
            controls
          />
          <text v-if="activeVideo === 'skeleton'" class="pose-video-note">骨架动画由采样帧拼接，帧率较慢，仅示意</text>
        </view>

        <scroll-view v-else-if="skeletonFrameSrcs.length > 0" scroll-x class="skeleton-frames">
          <view v-for="(src, i) in skeletonFrameSrcs" :key="i" class="skeleton-frame">
            <image :src="src" mode="aspectFill" class="skeleton-frame-img" />
          </view>
        </scroll-view>
      </view>

      <!-- 节奏与战术 -->
      <view v-if="report?.rhythm" class="form-card">
        <text class="card-title">🎵 节奏与战术</text>
        <text class="card-text">{{ report.rhythm }}</text>
      </view>

      <!-- 亮点总结 -->
      <view v-if="report && report.strengths && report.strengths.length > 0" class="form-card">
        <text class="card-title">⭐ 亮点总结</text>
        <view v-for="(s, i) in report.strengths" :key="i" class="strength-item">
          <text class="strength-index">{{ i + 1 }}</text>
          <text class="card-text">{{ s }}</text>
        </view>
      </view>

      <!-- 待改进 & 建议 -->
      <view v-if="report && report.improvements && report.improvements.length > 0" class="form-card">
        <text class="card-title">🎯 待改进 & 建议</text>
        <view v-for="(im, i) in report.improvements" :key="i" class="impr-item">
          <text class="impr-issue">⚠️ {{ im.issue }}</text>
          <text class="impr-advice">💡 {{ im.advice }}</text>
        </view>
      </view>

      <!-- 删除 -->
      <view class="delete-btn press-btn" @tap="confirmRemove">删除这条分析</view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { onLoad } from "@dcloudio/uni-app";

import RadarChart from "@/components/RadarChart.vue";
import { deleteAnalysis, getAnalysis } from "@/services/data";
import type { Analysis } from "@/types";
import { resolveUploadUrl, safeNavigateBack } from "@/utils";

const analysis = ref<Analysis | null>(null);
const report = computed(() => analysis.value?.report);
const pose = computed(() => analysis.value?.pose);

/** 封面：优先骨架标注帧（相对 media URL），兼容旧 base64 封面 */
const coverSrc = computed(() => resolveUploadUrl(analysis.value?.thumb || ""));

const activeVideo = ref<"original" | "skeleton">("original");

const originalVideoSrc = computed(() => resolveUploadUrl(analysis.value?.video_url || ""));
const skeletonVideoSrc = computed(() => resolveUploadUrl(pose.value?.skeleton_video_url || ""));
const skeletonFrameSrcs = computed(() =>
  (pose.value?.skeleton_frames || []).map(resolveUploadUrl),
);

/** 当前播放的视频地址：骨架模式时优先骨架动画，否则回退原视频 */
const activeVideoSrc = computed(() => {
  if (activeVideo.value === "skeleton" && skeletonVideoSrc.value) return skeletonVideoSrc.value;
  if (activeVideo.value === "original" && originalVideoSrc.value) return originalVideoSrc.value;
  return skeletonVideoSrc.value || originalVideoSrc.value;
});

/** 分数 → 进度条宽度（0-100 映射 0-100%） */
function dimWidth(score: number): string {
  const v = Math.max(0, Math.min(100, Number(score) || 0));
  return `${v}%`;
}

onLoad(async (query) => {
  const id = Number(query?.id);
  if (!id) {
    uni.showToast({ title: "参数错误", icon: "none" });
    return;
  }
  try {
    analysis.value = await getAnalysis(id);
  } catch {
    uni.showToast({ title: "报告加载失败", icon: "none" });
  }
});

function confirmRemove() {
  if (!analysis.value) return;
  uni.showModal({
    title: "删除分析",
    content: "确定删除这条分析记录？",
    confirmColor: "#A8B822",
    success: async (res) => {
      if (!res.confirm || !analysis.value) return;
      try {
        await deleteAnalysis(analysis.value.id);
        uni.showToast({ title: "已删除", icon: "success" });
        setTimeout(() => safeNavigateBack("/pages/coach/coach"), 600);
      } catch (e) {
        const msg = e instanceof Error ? e.message : "删除失败";
        uni.showToast({ title: msg, icon: "none" });
      }
    },
  });
}
</script>

<style scoped lang="scss">
.report-page {
  min-height: 100vh;
  background-color: $color-paper;
}

.report-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  font-size: 13px;
  color: $color-olive-light;
}

.report-body {
  padding: $space-lg;
  padding-top: $space-xl;
  display: flex;
  flex-direction: column;
  gap: $space-md;
}

// ========== 封面 ==========
.cover-wrap {
  position: relative;
}

.cover-img {
  width: 100%;
  border-radius: $radius-card;
  background-color: $color-olive;
}

.cover-placeholder {
  width: 100%;
  height: 176px;
  border-radius: $radius-card;
  background-color: $color-olive;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 40px;
}

.score-badge {
  position: absolute;
  right: 20px;
  bottom: -16px;
  width: 72px;
  height: 72px;
  border-radius: 50%;
  background: radial-gradient(circle at 30% 25%, rgba(255, 255, 255, 0.45), transparent 55%);
  background-color: $color-lime;
  border: 4px solid $color-paper;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.score-badge-value {
  font-size: 26px;
  font-weight: 800;
  line-height: 1.1;
  color: $color-ink;
}

.score-badge-label {
  font-size: 9px;
  font-weight: 600;
  opacity: 0.7;
  color: $color-ink;
}

.skeleton-badge {
  position: absolute;
  left: 12px;
  bottom: 12px;
  font-size: 11px;
  font-weight: 600;
  color: $color-ink;
  background: rgba(200, 218, 43, 0.92);
  border-radius: 9999px;
  padding: 4px 10px;
}

// ========== 雷达图 ==========
.radar-chart {
  margin-bottom: $space-lg;
}

// ========== 姿态测量 ==========
.pose-metrics {
  display: flex;
  gap: $space-sm;
  margin-bottom: $space-lg;
}

.pose-metric {
  flex: 1;
  background-color: $color-paper;
  border-radius: 16px;
  padding: 12px 0;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.pose-metric-value {
  font-size: 20px;
  font-weight: 700;
  color: $color-lime-dark;
}

.pose-metric-label {
  margin-top: 2px;
  font-size: 11px;
  color: $color-olive-light;
}

.pose-none {
  display: block;
  font-size: 13px;
  color: $color-olive-light;
  margin-bottom: $space-md;
}

.pose-video {
  border-radius: 16px;
  overflow: hidden;
}

.video-toggle {
  display: flex;
  gap: 8px;
  margin-bottom: $space-sm;
}

.video-toggle-pill {
  font-size: 12px;
  color: $color-olive-light;
  background-color: $color-paper;
  border-radius: 9999px;
  padding: 6px 14px;

  &--active {
    color: $color-ink;
    background-color: $color-lime;
    font-weight: 600;
  }
}

.pose-video-el {
  width: 100%;
  border-radius: 12px;
  background-color: $color-olive;
}

.pose-video-note {
  display: block;
  margin-top: 6px;
  font-size: 11px;
  color: $color-olive-light;
}

.skeleton-frames {
  white-space: nowrap;
  width: 100%;
}

.skeleton-frame {
  display: inline-block;
  width: 88px;
  height: 88px;
  border-radius: 12px;
  overflow: hidden;
  margin-right: 8px;

  &:last-child {
    margin-right: 0;
  }
}

.skeleton-frame-img {
  width: 100%;
  height: 100%;
}

// ========== 摘要 ==========
.summary-block {
  padding: $space-lg $space-sm $space-sm;
}

.summary-tags {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.tag-kind {
  font-size: 12px;
  font-weight: 700;
  color: $color-ink;
  background: $color-lime;
  border-radius: 9999px;
  padding: 3px 10px;
}

.tag-ntrp {
  font-size: 12px;
  font-weight: 700;
  color: $color-lime;
  background: $color-olive;
  border-radius: 9999px;
  padding: 3px 10px;
}

.tag-mode {
  font-size: 12px;
  color: $color-olive-light;
}

.summary-text {
  display: block;
  margin-top: 8px;
  font-size: 15px;
  font-weight: 600;
  color: $color-ink;
  line-height: 1.5;
}

.ntrp-note {
  display: block;
  margin-top: 4px;
  font-size: 11px;
  color: $color-olive-light;
}

// ========== 卡片 ==========
.form-card {
  background-color: $color-white;
  border-radius: $radius-card;
  padding: $space-lg;
  box-shadow: $shadow-card;
}

.card-title {
  display: block;
  font-size: $font-size-base;
  font-weight: 600;
  color: $color-ink;
  margin-bottom: $space-md;
}

.card-text {
  display: block;
  font-size: 13px;
  color: $color-olive-light;
  line-height: 1.7;
}

// ========== 六维 ==========
.dim-item {
  margin-bottom: $space-md;

  &:last-child {
    margin-bottom: 0;
  }
}

.dim-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 4px;
}

.dim-name {
  font-size: 14px;
  font-weight: 600;
  color: $color-ink;
}

.dim-score {
  font-size: 15px;
  font-weight: 700;
  color: $color-lime-dark;
}

.dim-bar {
  height: 8px;
  border-radius: 9999px;
  background-color: $color-paper;
  overflow: hidden;
}

.dim-bar-fill {
  height: 100%;
  border-radius: 9999px;
  background-color: $color-lime;
}

.dim-comment {
  display: block;
  margin-top: 4px;
  font-size: 12px;
  color: $color-olive-light;
  line-height: 1.5;
}

// ========== 亮点 / 建议 ==========
.strength-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: $space-sm;

  &:last-child {
    margin-bottom: 0;
  }
}

.strength-index {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background-color: $color-lime;
  color: $color-ink;
  font-size: 11px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-top: 1px;
}

.impr-item {
  background-color: $color-paper;
  border-radius: 16px;
  padding: $space-md;
  margin-bottom: $space-sm;

  &:last-child {
    margin-bottom: 0;
  }
}

.impr-issue {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: $color-ink;
  line-height: 1.5;
}

.impr-advice {
  display: block;
  margin-top: 6px;
  font-size: 12px;
  color: $color-olive-light;
  line-height: 1.6;
}

// ========== 删除 ==========
.delete-btn {
  margin-top: $space-sm;
  text-align: center;
  font-size: 14px;
  color: #e05c5c;
  padding: 14px 0;
  background-color: $color-white;
  border-radius: $radius-card;
  box-shadow: $shadow-card;
}
</style>