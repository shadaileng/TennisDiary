<template>
  <view class="container" v-if="analysis">
    <!-- 离线提示：缓存命中但无网络时媒体占位 -->
    <view v-if="offline" class="offline-banner">
      <text>📡 离线浏览中：文字报告来自本地缓存，视频/封面需联网后查看</text>
    </view>

    <!-- 头部 -->
    <view class="header">
      <image
        class="cover"
        :src="imgSrc(analysis.thumb || '')"
        mode="aspectFill"
        @error="onImgError(analysis.thumb || '')"
      />
      <view class="header-info">
        <text class="title">{{ analysis.kind }}<text v-if="analysis.mode" class="analysis-mode"> · {{ analysis.mode === 'full' ? '综合' : '单次' }}</text></text>
        <text class="sub">{{ analysis.date }}</text>
        <view class="score-badge" v-if="analysis.score != null">
          <text>总分 {{ analysis.score }}</text>
        </view>
      </view>
    </view>

    <!-- 摘要 -->
    <view class="section" v-if="analysis.summary">
      <text class="section-title">总体点评</text>
      <text class="summary-text">{{ analysis.summary }}</text>
    </view>

    <!-- 高光 / 骨架帧 -->
    <view class="section" v-if="analysis.highlights && analysis.highlights.length">
      <text class="section-title">高光帧</text>
      <view class="frame-row">
        <image
          v-for="(h, i) in analysis.highlights"
          :key="i"
          class="frame"
          :src="imgSrc(h)"
          mode="aspectFill"
          @error="onImgError(h)"
        />
      </view>
    </view>

    <!-- 视频 -->
    <view class="section" v-if="analysis.video_url">
      <text class="section-title">分析视频</text>
      <view class="video-wrap">
        <video
          v-if="networkOnline"
          class="hl-video"
          :src="resolveMediaSrc(analysis.video_url || '', true)"
          controls
          :poster="imgSrc(analysis.thumb || '')"
        />
        <view v-else class="video-mask">
          <image class="mask-img" :src="OFFLINE_MEDIA_PLACEHOLDER" mode="aspectFill" />
          <text class="mask-text">网络不可用，请联网后查看</text>
        </view>
      </view>
    </view>

    <!-- 维度得分 -->
    <view class="section" v-if="analysis.report && analysis.report.dimensions.length">
      <text class="section-title">维度得分</text>
      <view class="dim-item" v-for="(d, i) in analysis.report.dimensions" :key="i">
        <view class="dim-head">
          <text class="dim-name">{{ d.name }}</text>
          <text class="dim-score">{{ d.score }}</text>
        </view>
        <text class="dim-comment">{{ d.comment }}</text>
      </view>
    </view>

    <!-- 姿态 -->
    <view class="section" v-if="analysis.pose && analysis.pose.detected">
      <text class="section-title">姿态分析</text>
      <view class="frame-row" v-if="analysis.pose.skeleton_frames && analysis.pose.skeleton_frames.length">
        <image
          v-for="(s, i) in analysis.pose.skeleton_frames"
          :key="i"
          class="frame"
          :src="imgSrc(s)"
          mode="aspectFill"
          @error="onImgError(s)"
        />
      </view>
      <view class="video-wrap" v-if="analysis.pose.skeleton_video_url">
        <video
          v-if="networkOnline"
          class="hl-video"
          :src="resolveMediaSrc(analysis.pose.skeleton_video_url || '', true)"
          controls
        />
        <view v-else class="video-mask">
          <image class="mask-img" :src="OFFLINE_MEDIA_PLACEHOLDER" mode="aspectFill" />
          <text class="mask-text">网络不可用，请联网后查看</text>
        </view>
      </view>
      <text class="pose-metrics" v-if="analysis.pose.metrics">
        肘角 {{ analysis.pose.metrics.elbowAngle }}° · 膝角 {{ analysis.pose.metrics.kneeAngle }}° · 躯干倾角 {{ analysis.pose.metrics.trunkLean }}°
      </text>
    </view>

    <!-- 改进建议 -->
    <view class="section" v-if="analysis.report && analysis.report.improvements.length">
      <text class="section-title">改进建议</text>
      <view class="improve-item" v-for="(im, i) in analysis.report.improvements" :key="i">
        <text class="improve-issue">· {{ im.issue }}</text>
        <text class="improve-advice">{{ im.advice }}</text>
      </view>
    </view>

    <!-- 加载中（首次无缓存） -->
    <view v-if="loading" class="loading-tip">
      <text>加载中…</text>
    </view>
  </view>
</template>

<script setup lang="ts">
import { onLoad } from "@dcloudio/uni-app";
import { ref } from "vue";
import { getAnalysis } from "@/services/data";
import { getAnalysisDetail, setAnalysisDetail } from "@/services/cloudCache";
import { useAuthStore } from "@/stores/auth";
import { networkOnline } from "@/utils/network";
import { resolveMediaSrc, OFFLINE_MEDIA_PLACEHOLDER } from "@/utils/media";
import type { ApiError } from "@/services/request";
import type { Analysis } from "@/types";

const analysis = ref<Analysis | null>(null);
const loading = ref(false);
const offline = ref(false);
/** 媒体加载失败（URL 失效/401）回退占位的 url 集合 */
const failedImages = ref<Set<string>>(new Set());

const auth = useAuthStore();
let id = 0;
let timer: ReturnType<typeof setInterval> | undefined;

function imgSrc(url: string): string {
  if (!url) return OFFLINE_MEDIA_PLACEHOLDER;
  if (failedImages.value.has(url)) return OFFLINE_MEDIA_PLACEHOLDER;
  return resolveMediaSrc(url, networkOnline.value);
}

function onImgError(url: string) {
  failedImages.value.add(url);
}

function subscribe() {
  if (timer || !networkOnline.value) return;
  timer = setInterval(async () => {
    try {
      const detail = await getAnalysis(id);
      analysis.value = detail;
      const u = auth.user?.id;
      if (u != null) setAnalysisDetail(u, detail);
      if (detail.status === "completed" || detail.status === "failed") {
        if (timer) clearInterval(timer);
        timer = undefined;
      }
    } catch {
      if (timer) clearInterval(timer);
      timer = undefined;
    }
  }, 3000);
}

async function load() {
  if (!id) return;
  const u = auth.user?.id;
  // 缓存优先：立即渲染详情（离线可看文字报告与骨架帧占位）
  if (u != null) {
    const cached = getAnalysisDetail(u, id);
    if (cached) analysis.value = cached;
  }
  if (!networkOnline.value) {
    offline.value = true;
    return;
  }
  loading.value = true;
  try {
    const detail = await getAnalysis(id);
    analysis.value = detail;
    if (u != null) setAnalysisDetail(u, detail);
    offline.value = false;
    if (detail.status === "processing") subscribe();
  } catch (e) {
    const err = e as ApiError;
    if (err && err.status === -1) {
      offline.value = true;
    } else {
      offline.value = false;
    }
  } finally {
    loading.value = false;
  }
}

onLoad((q) => {
  id = Number(q?.id);
  load();
});
</script>

<style scoped>
.container {
  padding: 24rpx;
  box-sizing: border-box;
}
.offline-banner {
  background: #fff7e6;
  border: 1rpx solid #ffd591;
  color: #ad6800;
  padding: 12rpx 20rpx;
  border-radius: 12rpx;
  margin-bottom: 16rpx;
  font-size: 24rpx;
}
.header {
  display: flex;
  background: #fff;
  border-radius: 16rpx;
  padding: 16rpx;
}
.cover {
  width: 200rpx;
  height: 200rpx;
  border-radius: 12rpx;
  background: #f0f0f0;
}
.header-info {
  flex: 1;
  margin-left: 20rpx;
  display: flex;
  flex-direction: column;
  justify-content: center;
}
.title {
  font-size: 32rpx;
  font-weight: 600;
  color: #222;
}
.analysis-mode {
  font-size: 24rpx;
  font-weight: 400;
  color: #999;
}
.sub {
  font-size: 24rpx;
  color: #999;
  margin-top: 8rpx;
}
.score-badge {
  margin-top: 16rpx;
  align-self: flex-start;
  background: #f9f0ff;
  color: #722ed1;
  font-size: 24rpx;
  padding: 6rpx 16rpx;
  border-radius: 10rpx;
}
.section {
  margin-top: 24rpx;
  background: #fff;
  border-radius: 16rpx;
  padding: 20rpx;
}
.section-title {
  font-size: 28rpx;
  font-weight: 600;
  color: #333;
  display: block;
  margin-bottom: 16rpx;
}
.summary-text {
  font-size: 26rpx;
  color: #555;
  line-height: 1.6;
}
.frame-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12rpx;
}
.frame {
  width: 200rpx;
  height: 200rpx;
  border-radius: 12rpx;
  background: #f0f0f0;
}
.video-wrap {
  margin-top: 8rpx;
}
.hl-video {
  width: 100%;
  height: 360rpx;
  border-radius: 12rpx;
  background: #000;
}
.video-mask {
  position: relative;
  width: 100%;
  height: 360rpx;
  border-radius: 12rpx;
  overflow: hidden;
}
.mask-img {
  width: 100%;
  height: 100%;
  filter: grayscale(1);
}
.mask-text {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  text-align: center;
  background: rgba(0, 0, 0, 0.5);
  color: #fff;
  font-size: 24rpx;
  padding: 12rpx 0;
}
.dim-item {
  padding: 12rpx 0;
  border-top: 1rpx solid #f0f0f0;
}
.dim-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.dim-name {
  font-size: 28rpx;
  font-weight: 600;
  color: #222;
}
.dim-score {
  font-size: 26rpx;
  color: #722ed1;
}
.dim-comment {
  font-size: 26rpx;
  color: #555;
  margin-top: 6rpx;
}
.pose-metrics {
  display: block;
  font-size: 24rpx;
  color: #888;
  margin-top: 12rpx;
}
.improve-item {
  padding: 12rpx 0;
  border-top: 1rpx solid #f0f0f0;
}
.improve-issue {
  font-size: 26rpx;
  color: #333;
}
.improve-advice {
  display: block;
  font-size: 26rpx;
  color: #555;
  margin-top: 6rpx;
  line-height: 1.6;
}
.loading-tip {
  text-align: center;
  color: #999;
  padding: 40rpx 0;
  font-size: 28rpx;
}
</style>
