<template>
  <page-meta :page-style="themeStyle" :background-color="themeBg" />
  <view class="coach-page">
    <!-- hero 卡（深橄榄渐变 + 青柠光斑） -->
    <view class="hero-card">
      <text class="hero-badge">🎾 7×24H · 专属私教</text>
      <text class="hero-title">上传视频，让教练帮你复盘</text>
      <view class="hero-features">
        <text v-for="f in FEATURES" :key="f" class="hero-feature">{{ f }}</text>
      </view>
      <view class="hero-btn press-btn" @tap="goAnalyze">开始分析</view>
    </view>

    <!-- 历史分析 -->
    <view class="history-header">
      <text class="history-title">历史分析</text>
      <text class="history-count">{{ analyses.length }} 条</text>
    </view>

    <Empty v-if="analyses.length === 0" icon="🎥" text="还没有分析记录" buttonText="去分析" @action="goAnalyze" />

    <view v-else class="history-list">
      <view
        v-for="a in analyses"
        :key="a.id"
        class="history-item press-btn"
        @tap="goReport(a.id)"
      >
        <view class="history-thumb">
          <image v-if="a.thumb" :src="resolveUploadUrl(a.thumb)" mode="aspectFill" class="history-thumb-img" />
          <text v-else class="history-thumb-placeholder">🎾</text>
          <text v-if="a.pose?.detected" class="thumb-badge">🦴</text>
        </view>
        <view class="history-info">
          <view class="history-tags">
            <text class="tag-kind">{{ a.kind }}</text>
            <text class="tag-mode">{{ a.mode === "single" ? "单次挥拍" : "综合分析" }} · {{ a.date }}</text>
          </view>
          <text class="history-summary">{{ a.summary || "暂无摘要" }}</text>
        </view>
        <view class="history-score">
          <template v-if="(a.score || 0) > 0">
            <text class="score-value">{{ a.score }}</text>
            <text class="score-label">评分</text>
          </template>
          <text v-else class="score-local">本地</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { onShow } from "@dcloudio/uni-app";

import Empty from "@/components/Empty.vue";
import { useThemeStyle } from "@/composables/useTheme";
import { getAnalyses } from "@/services/data";
import type { Analysis } from "@/types";
import { resolveUploadUrl } from "@/utils";
import { createTraceId, logError, logInfo } from "@/utils/eventLogger";

const { themeStyle, themeBg } = useThemeStyle();

const FEATURES = ["骨架追踪", "六维评分", "改进建议", "高光时刻"];

const analyses = ref<Analysis[]>([]);

onShow(async () => {
  const traceId = createTraceId();
  logInfo("加载历史分析", { trace_id: traceId }, "analyses_load", traceId);
  try {
    const data = await getAnalyses();
    analyses.value = data.items || [];
    logInfo("历史分析加载成功", { trace_id: traceId, count: analyses.value.length }, "analyses_loaded", traceId);
  } catch (e) {
    analyses.value = [];
    logError("历史分析加载失败", { trace_id: traceId, error: (e as Error).message }, "analyses_load_failed", undefined, traceId);
  }
});

function goAnalyze() {
  uni.navigateTo({ url: "/pages/coach/analyze" });
}

function goReport(id: number) {
  uni.navigateTo({ url: `/pages/coach/report?id=${id}` });
}
</script>

<style scoped lang="scss">
.coach-page {
  min-height: 100vh;
  background-color: var(--color-page-bg, #F2F2EF);
  padding: $space-lg;
  padding-bottom: $space-3xl;
  box-sizing: border-box;
}

// ========== hero 卡 ==========
.hero-card {
  position: relative;
  overflow: hidden;
  background: linear-gradient(135deg, var(--color-hero-a, #242B1F), var(--color-hero-b, #3A4433));
  border-radius: $radius-card;
  padding: $space-lg;
  margin-bottom: $space-lg;
  display: flex;
  flex-direction: column;
  align-items: flex-start;

  &::before {
    content: "";
    position: absolute;
    top: -80px;
    right: -40px;
    width: 200px;
    height: 200px;
    border-radius: 50%;
    background: rgba(var(--color-accent-rgb, 200, 218, 43), 0.16);
    filter: blur(36px);
  }
}

.hero-badge {
  position: relative;
  z-index: 1;
  font-size: 11px;
  color: var(--color-accent, #C8DA2B);
  background: rgba(var(--color-accent-rgb, 200, 218, 43), 0.14);
  border: 1px solid rgba(var(--color-accent-rgb, 200, 218, 43), 0.3);
  border-radius: 9999px;
  padding: 4px 10px;
  letter-spacing: 1px;
}

.hero-title {
  position: relative;
  z-index: 1;
  display: block;
  margin-top: 14px;
  font-size: 22px;
  font-weight: 700;
  color: $color-white;
  line-height: 1.4;
}

.hero-features {
  position: relative;
  z-index: 1;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 14px;
}

.hero-feature {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.78);
  background: rgba(255, 255, 255, 0.1);
  border-radius: 9999px;
  padding: 4px 10px;
}

.hero-btn {
  position: relative;
  z-index: 1;
  margin-top: 20px;
  background: var(--color-accent, #C8DA2B);
  color: $color-ink;
  font-size: 15px;
  font-weight: 600;
  padding: 12px 28px;
  border-radius: 9999px;
  box-shadow: 0 4px 12px rgba(var(--color-accent-rgb, 200, 218, 43), 0.35);
}

// ========== 历史分析 ==========
.history-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px $space-sm;
}

.history-title {
  font-size: 17px;
  font-weight: 600;
  color: $color-ink;
}

.history-count {
  font-size: 12px;
  color: $color-olive-light;
}

.history-list {
  margin-top: $space-md;
  display: flex;
  flex-direction: column;
  gap: $space-sm;
}

.history-item {
  background: $color-white;
  border-radius: $radius-card;
  box-shadow: $shadow-card;
  padding: $space-md;
  display: flex;
  align-items: center;
  gap: $space-md;
}

.history-thumb {
  position: relative;
  width: 64px;
  height: 64px;
  border-radius: 16px;
  overflow: hidden;
  background-color: $color-olive;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.history-thumb-img {
  width: 100%;
  height: 100%;
}

.history-thumb-placeholder {
  font-size: 26px;
}

.thumb-badge {
  position: absolute;
  right: 2px;
  bottom: 2px;
  font-size: 12px;
  background: var(--color-accent, #C8DA2B);
  border: 2px solid $color-white;
  border-radius: 50%;
  width: 22px;
  height: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.history-info {
  flex: 1;
  min-width: 0;
}

.history-tags {
  display: flex;
  align-items: center;
  gap: 6px;
}

.tag-kind {
  font-size: 11px;
  font-weight: 700;
  color: $color-ink;
  background: var(--color-accent, #C8DA2B);
  border-radius: 9999px;
  padding: 2px 8px;
}

.tag-mode {
  font-size: 11px;
  color: $color-olive-light;
}

.history-summary {
  display: block;
  margin-top: 6px;
  font-size: 13px;
  color: $color-olive-light;
  line-height: 1.5;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.history-score {
  flex-shrink: 0;
  text-align: center;
}

.score-value {
  display: block;
  font-size: 22px;
  font-weight: 700;
  color: var(--color-accent-dark, #A8B822);
  line-height: 1.2;
}

.score-label {
  font-size: 10px;
  color: $color-olive-light;
}

.score-local {
  font-size: 11px;
  color: $color-olive-light;
}
</style>