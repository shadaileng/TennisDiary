<template>
  <view class="container">
    <!-- 离线横幅：缓存命中但当前无网络 -->
    <view v-if="offline && analyses.length > 0" class="offline-banner">
      <text>📡 离线浏览中，数据来自本地缓存</text>
    </view>

    <!-- 列表 -->
    <view v-if="analyses.length > 0" class="analysis-list">
      <navigator
        v-for="a in analyses"
        :key="a.id"
        :url="`/pages/coach/report?id=${a.id}`"
        class="analysis-card"
        hover-class="card-hover"
      >
        <image
          class="analysis-thumb"
          :src="thumbSrc(a)"
          mode="aspectFill"
          @error="onThumbError(a.id)"
        />
        <view class="analysis-info">
          <text class="analysis-title">{{ a.kind }}<text v-if="a.mode" class="analysis-mode"> · {{ a.mode === 'full' ? '综合' : '单次' }}</text></text>
          <text class="analysis-sub">{{ a.date }}</text>
          <view class="analysis-tags">
            <text v-if="a.status === 'processing'" class="tag tag-processing">分析中</text>
            <text v-else-if="a.status === 'completed'" class="tag tag-done">已完成</text>
            <text v-else-if="a.status === 'failed'" class="tag tag-fail">失败</text>
            <text v-if="a.score != null" class="tag tag-score">总分 {{ a.score }}</text>
          </view>
        </view>
      </navigator>
    </view>

    <!-- 加载中（首次无缓存且正在请求） -->
    <view v-else-if="loading" class="empty-state">
      <text>加载中…</text>
    </view>

    <!-- 空态：无缓存且无网络 / 确实无数据 -->
    <view v-else class="empty-state">
      <text v-if="offline">网络不可用，暂无可浏览的本地分析</text>
      <text v-else>还没有分析记录，去上传一段训练视频吧</text>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { onShow } from "@dcloudio/uni-app";
import { getAnalyses, getAnalysis } from "@/services/data";
import { getAnalysesCache, setAnalysesCache } from "@/services/cloudCache";
import { useAuthStore } from "@/stores/auth";
import { networkOnline } from "@/utils/network";
import { resolveMediaSrc, OFFLINE_MEDIA_PLACEHOLDER } from "@/utils/media";
import type { ApiError } from "@/services/request";
import type { Analysis } from "@/types";

const auth = useAuthStore();
const uid = computed(() => auth.user?.id ?? null);

const analyses = ref<Analysis[]>([]);
const loading = ref(false);
const offline = ref(false);
/** 缩略图加载失败（URL 失效/401）后回退占位的 id 集合 */
const failedThumbs = ref<Set<number>>(new Set());

/** 订阅仍在处理中的分析；离线时跳过 */
const timers: Record<number, ReturnType<typeof setInterval>> = {};
function subscribeIfProcessing(a: Analysis) {
  if (!networkOnline.value || timers[a.id]) return;
  timers[a.id] = setInterval(async () => {
    try {
      const detail = await getAnalysis(a.id);
      const idx = analyses.value.findIndex((x) => x.id === a.id);
      if (idx >= 0) analyses.value[idx] = detail;
      if (detail.status === "completed" || detail.status === "failed") {
        clearInterval(timers[a.id]);
        delete timers[a.id];
        const u = uid.value;
        if (u != null) setAnalysesCache(u, analyses.value);
      }
    } catch {
      clearInterval(timers[a.id]);
      delete timers[a.id];
    }
  }, 3000);
}

async function loadAnalyses() {
  const id = uid.value;
  if (id == null) {
    analyses.value = [];
    return;
  }
  // 缓存优先：立即渲染缓存（离线可直接浏览历史列表与文字报告）
  const cached = getAnalysesCache(id);
  analyses.value = cached;
  failedThumbs.value = new Set();
  if (!networkOnline.value) {
    offline.value = true;
    return;
  }
  loading.value = true;
  try {
    const data = await getAnalyses();
    const items = data.items || [];
    setAnalysesCache(id, items);
    analyses.value = items;
    offline.value = false;
    items.forEach((a) => {
      if (a.status === "processing") subscribeIfProcessing(a);
    });
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

function thumbSrc(a: Analysis): string {
  if (failedThumbs.value.has(a.id)) return OFFLINE_MEDIA_PLACEHOLDER;
  return resolveMediaSrc(a.thumb || "", networkOnline.value);
}

function onThumbError(id: number) {
  failedThumbs.value.add(id);
}

onShow(() => {
  loadAnalyses();
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
.analysis-list {
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}
.analysis-card {
  display: flex;
  background: #fff;
  border-radius: 16rpx;
  padding: 16rpx;
  box-shadow: 0 2rpx 8rpx rgba(0, 0, 0, 0.05);
}
.card-hover {
  opacity: 0.9;
}
.analysis-thumb {
  width: 160rpx;
  height: 160rpx;
  border-radius: 12rpx;
  background: #f0f0f0;
}
.analysis-info {
  flex: 1;
  margin-left: 20rpx;
  display: flex;
  flex-direction: column;
  justify-content: center;
}
.analysis-title {
  font-size: 30rpx;
  font-weight: 600;
  color: #222;
}
.analysis-mode {
  font-size: 24rpx;
  font-weight: 400;
  color: #999;
}
.analysis-sub {
  font-size: 24rpx;
  color: #999;
  margin-top: 8rpx;
}
.analysis-tags {
  display: flex;
  gap: 12rpx;
  margin-top: 12rpx;
}
.tag {
  font-size: 22rpx;
  padding: 4rpx 12rpx;
  border-radius: 8rpx;
}
.tag-processing {
  background: #e6f7ff;
  color: #1890ff;
}
.tag-done {
  background: #f6ffed;
  color: #52c41a;
}
.tag-fail {
  background: #fff1f0;
  color: #f5222d;
}
.tag-score {
  background: #f9f0ff;
  color: #722ed1;
}
.empty-state {
  text-align: center;
  color: #999;
  padding: 80rpx 0;
  font-size: 28rpx;
}
</style>
