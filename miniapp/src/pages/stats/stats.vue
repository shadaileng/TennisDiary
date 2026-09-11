<template>
  <page-meta :page-style="themeStyle" :background-color="themeBg" />
  <view class="stats-page">
    <!-- 游客横幅：本地数据提示 -->
    <view v-if="authStore.isGuest" class="guest-banner">
      <text class="guest-banner__text">游客模式：数据仅保存在本机，登录后自动同步到云端</text>
    </view>

    <!-- 离线横幅：统计数据来自本地缓存兜底 -->
    <view v-if="!authStore.isGuest && offlineStats" class="offline-banner">
      <text>📡 离线浏览中，统计为本地缓存估算（可能不含最新云端数据）</text>
    </view>

    <!-- 汇总卡片 -->
    <view class="stats-summary">
      <view class="stats-summary-header">
        <text class="stats-summary-title">数据总览</text>
        <MoneyToggle />
      </view>

      <!-- 空态：没有任何统计数据 -->
      <view v-if="!statsLoading && stats && !hasAnyData" class="stats-empty">
        <Empty
          icon="📊"
          text="还没有任何打球数据，从记录第一篇日记开始吧"
          button-text="去记录"
          @action="goDiary"
        />
      </view>

      <!-- 统计卡片 -->
      <view v-else class="stats-grid">
        <view class="stats-card">
          <text class="stats-card-label">累计打球</text>
          <text class="stats-card-value">
            {{ stats?.total_sessions ?? 0 }}
            <text class="stats-card-unit">次</text>
          </text>
        </view>
        <view class="stats-card">
          <text class="stats-card-label">累计时长</text>
          <text class="stats-card-value">{{ fmtDuration(stats?.total_duration ?? 0) }}</text>
        </view>
        <view class="stats-card">
          <text class="stats-card-label">平均强度</text>
          <text class="stats-card-value">{{ (stats?.avg_intensity ?? 0).toFixed(1) }}</text>
        </view>
        <view class="stats-card">
          <text class="stats-card-label">平均心情</text>
          <text class="stats-card-value">{{ (stats?.avg_mood ?? 0).toFixed(1) }}</text>
        </view>
        <view class="stats-card">
          <text class="stats-card-label">总花费</text>
          <text class="stats-card-value stats-card-value--cost">{{ costText }}</text>
        </view>
        <view class="stats-card">
          <text class="stats-card-label">装备数</text>
          <text class="stats-card-value">
            {{ stats?.total_gears ?? 0 }}
            <text class="stats-card-unit">件</text>
          </text>
        </view>
      </view>
    </view>

    <!-- 体重管理 -->
    <view class="stats-weight">
      <view class="stats-weight-header">
        <text class="stats-weight-title">体重管理</text>
        <text class="stats-weight-add" @tap="openForm">＋ 记录</text>
      </view>

      <!-- 三格 -->
      <view class="stats-weight-grid">
        <view class="stats-weight-card">
          <text class="stats-weight-card-label">当前</text>
          <text class="stats-weight-card-value">{{ latest ? latest.weight : "—" }}</text>
          <text class="stats-weight-card-unit">kg</text>
        </view>
        <view class="stats-weight-card">
          <text class="stats-weight-card-label">累计变化</text>
          <text class="stats-weight-card-value" :class="deltaColor">{{ deltaText }}</text>
          <text class="stats-weight-card-unit">kg</text>
        </view>
        <view class="stats-weight-card">
          <text class="stats-weight-card-label">记录</text>
          <text class="stats-weight-card-value">{{ weightStore.weights.length }}</text>
          <text class="stats-weight-card-unit">次</text>
        </view>
      </view>

      <!-- 体重趋势折线图 -->
      <view v-if="weightData.length >= 2" class="stats-weight-chart">
        <text class="stats-weight-chart-title">体重趋势</text>
        <LineChart :data="weightData" :height="130" :color="settingsStore.themePalette.accent" unit="kg" />
      </view>

      <!-- 空态 -->
      <view v-if="!weightStore.loading && weightStore.weights.length === 0" class="stats-weight-empty">
        <Empty icon="⚖️" text="记录体重和三维，见证身材变化" button-text="记录第一条" @action="openForm" />
      </view>

      <!-- 历史记录 -->
      <view v-else-if="weightStore.weights.length > 0" class="stats-weight-list">
        <view
          v-for="w in weightStore.sortedWeights"
          :key="getEntryId(w)"
          class="stats-weight-item"
        >
          <text class="stats-weight-item-date">{{ w.date }}</text>
          <text class="stats-weight-item-value">{{ w.weight }} kg</text>
          <text v-if="w.bust || w.waist || w.hip" class="stats-weight-item-dims">
            {{ dimensionsText(w) }}
          </text>
          <text class="stats-weight-item-delete" @tap="confirmRemove(getEntryId(w))">×</text>
        </view>
      </view>
    </view>

    <!-- 记录体重弹层 -->
    <Popup v-model:show="showForm" title="记录体重">
      <text class="stats-form-title">记录体重</text>
      <view class="stats-form-body">
        <view class="stats-form-row">
          <text class="stats-form-label">日期</text>
          <picker mode="date" :value="form.date" @change="onDateChange">
            <view class="stats-form-input">{{ form.date }}</view>
          </picker>
        </view>
        <view class="stats-form-row">
          <text class="stats-form-label">体重（kg）*</text>
          <input
            class="stats-form-input"
            type="digit"
            placeholder="62.5"
            placeholder-class="stats-form-placeholder"
            :value="form.weight"
            @input="onWeightInput"
          />
        </view>
        <view class="stats-form-row stats-form-row--grid">
          <view class="stats-form-field">
            <text class="stats-form-label">胸围 cm</text>
            <input class="stats-form-input" type="digit" placeholder="选填" placeholder-class="stats-form-placeholder" :value="form.bust" @input="onBustInput" />
          </view>
          <view class="stats-form-field">
            <text class="stats-form-label">腰围 cm</text>
            <input class="stats-form-input" type="digit" placeholder="选填" placeholder-class="stats-form-placeholder" :value="form.waist" @input="onWaistInput" />
          </view>
          <view class="stats-form-field">
            <text class="stats-form-label">臀围 cm</text>
            <input class="stats-form-input" type="digit" placeholder="选填" placeholder-class="stats-form-placeholder" :value="form.hip" @input="onHipInput" />
          </view>
        </view>
        <view class="stats-form-save press-btn" @tap="save">保存记录</view>
      </view>
    </Popup>
  </view>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from "vue";
import { onShow } from "@dcloudio/uni-app";

import Empty from "@/components/Empty.vue";
import LineChart from "@/components/LineChart.vue";
import MoneyToggle from "@/components/MoneyToggle.vue";
import Popup from "@/components/Popup.vue";
import { useThemeStyle } from "@/composables/useTheme";
import { useAuthStore, useSettingsStore, useWeightStore, useDiaryStore, useGearStore } from "@/stores";
import { getStats } from "@/services/data";
import type { ApiError } from "@/services/request";
import { getPendingDiaries, getPendingGears } from "@/services/pendingRepo";
import { aggregateLocalStats } from "@/services/localStats";
import { fmtDuration, fmtMoney, todayStr } from "@/utils";
import { getEntryId } from "@/types";
import type { AnyWeight, Stats, WeightRecord } from "@/types";
import { createTraceId, logError, logInfo } from "@/utils/eventLogger";

const authStore = useAuthStore();
const weightStore = useWeightStore();
const diaryStore = useDiaryStore();
const gearStore = useGearStore();
const settingsStore = useSettingsStore();
const { themeStyle, themeBg } = useThemeStyle();

// ==================== 汇总 ====================

const stats = ref<Stats | null>(null);

/** 汇总统计加载中 */
const statsLoading = ref(false);

/** 汇总统计来自本地缓存兜底（离线） */
const offlineStats = ref(false);

/** 是否没有任何统计数据 */
const hasAnyData = computed(() =>
  stats.value
    ? stats.value.total_sessions > 0 ||
      stats.value.total_duration > 0 ||
      stats.value.total_cost > 0 ||
      stats.value.total_gears > 0
    : false,
);

/** 跳转到日记 Tab 记录 */
function goDiary() {
  uni.switchTab({ url: "/pages/diary/diary" });
}

const costText = computed(() =>
  settingsStore.hideAmounts ? "¥**" : fmtMoney(stats.value?.total_cost ?? 0),
);

// ==================== 体重 ====================

const showForm = ref(false);
const form = reactive({
  date: todayStr(),
  weight: "",
  bust: "",
  waist: "",
  hip: "",
});

/** 最近一条（按日期升序最后一条） */
const latest = computed<AnyWeight | null>(() => {
  const list = weightStore.sortedWeights;
  return list.length ? list[list.length - 1] : null;
});

const delta = computed(() => {
  const list = weightStore.sortedWeights;
  if (list.length < 2) return 0;
  return list[list.length - 1].weight - list[0].weight;
});

const deltaText = computed(() => {
  if (weightStore.sortedWeights.length <= 1) return "—";
  return `${delta.value > 0 ? "+" : ""}${delta.value.toFixed(1)}`;
});

const deltaColor = computed(() =>
  delta.value < 0 ? "stats-weight-card-value--down" : delta.value > 0 ? "stats-weight-card-value--up" : "",
);

/** 体重折线数据（最近 14 条，升序：旧→新） */
const weightData = computed(() =>
  [...weightStore.weights]
    .reverse()
    .slice(0, 14)
    .map((w) => ({ label: w.date.slice(5), value: w.weight })),
);

function dimensionsText(w: AnyWeight): string {
  const parts = [
    w.bust ? `胸${w.bust}` : "",
    w.waist ? `腰${w.waist}` : "",
    w.hip ? `臀${w.hip}` : "",
  ].filter(Boolean);
  return parts.join(" / ");
}

// ==================== 表单 ====================

function openForm() {
  showForm.value = true;
}

function onDateChange(e: any) {
  form.date = e.detail.value;
}

function onWeightInput(e: any) {
  form.weight = e.detail.value;
}

function onBustInput(e: any) {
  form.bust = e.detail.value;
}

function onWaistInput(e: any) {
  form.waist = e.detail.value;
}

function onHipInput(e: any) {
  form.hip = e.detail.value;
}

async function save() {
  const w = Number(form.weight);
  if (!w || w < 20 || w > 300) {
    uni.showToast({ title: "请填写有效体重", icon: "none" });
    return;
  }
  try {
    await weightStore.create({
      date: form.date,
      weight: w,
      bust: Number(form.bust) || undefined,
      waist: Number(form.waist) || undefined,
      hip: Number(form.hip) || undefined,
    });
    uni.showToast({ title: "已记录", icon: "success" });
    showForm.value = false;
    form.weight = "";
    form.bust = "";
    form.waist = "";
    form.hip = "";
  } catch (e) {
    const msg = e instanceof Error ? e.message : "保存失败";
    uni.showToast({ title: msg, icon: "none" });
  }
}

function confirmRemove(id: number | string) {
  uni.showModal({
    title: "删除记录",
    content: "删除这条体重记录？",
    confirmColor: settingsStore.themePalette.dark,
    success: async (res) => {
      if (!res.confirm) return;
      try {
        await weightStore.remove(id);
        uni.showToast({ title: "已删除", icon: "success" });
      } catch (e) {
        const msg = e instanceof Error ? e.message : "删除失败";
        uni.showToast({ title: msg, icon: "none" });
      }
    },
  });
}

// ==================== 生命周期 ====================

onShow(() => {
  const traceId = createTraceId();
  if (authStore.isGuest) {
    // 游客态：本地聚合（日记/装备），体重取本地仓库；均不发请求
    weightStore.fetchList();
    stats.value = aggregateLocalStats(getPendingDiaries(), getPendingGears());
    statsLoading.value = false;
    logInfo("游客本地统计聚合", { total_sessions: stats.value.total_sessions }, undefined, "stats_guest_local", traceId);
    return;
  }
  logInfo("加载统计数据", { }, undefined, "stats_load", traceId);
  weightStore.fetchList();
  // 日记/装备本地缓存合并视图（仅本地读，供离线兜底聚合）
  diaryStore.hydrate();
  gearStore.hydrate();
  statsLoading.value = true;
  offlineStats.value = false;
  getStats()
    .then((s) => {
      stats.value = s;
      logInfo("统计数据加载成功", { total_sessions: s.total_sessions, total_duration: s.total_duration, total_cost: s.total_cost, total_gears: s.total_gears }, undefined, "stats_loaded", traceId);
    })
    .catch((e) => {
      const err = e as ApiError;
      if (err && err.status === -1) {
        // 离线兜底：聚合本地缓存（云端快照 + 离线待同步），口径对齐 /api/stats
        stats.value = aggregateLocalStats(diaryStore.diaries, gearStore.gears);
        offlineStats.value = true;
        logInfo("离线统计兜底（本地聚合）", { total_sessions: stats.value.total_sessions }, undefined, "stats_offline_fallback", traceId);
      } else {
        logError("统计数据加载失败", { error: (err as Error).message }, undefined, "stats_load_failed", undefined, traceId);
      }
    })
    .finally(() => {
      statsLoading.value = false;
    });
});
</script>

<style scoped lang="scss">

.stats-page {
  background-color: var(--color-page-bg, #F2F2EF);
  min-height: 100vh;
  padding-bottom: $space-3xl;
}

.guest-banner {
  margin: $space-md $space-md 0;
  padding: $space-sm $space-md;
  border-radius: $radius-card;
  background-color: var(--color-accent-soft, #F0F5CE);
  color: var(--color-accent-dark, #A8B822);
  font-size: 12px;
  line-height: 1.4;
}

.offline-banner {
  margin: $space-md $space-md 0;
  padding: $space-sm $space-md;
  border-radius: $radius-card;
  background-color: #fff7e6;
  color: #ad6800;
  font-size: 12px;
  line-height: 1.4;
}

// 汇总
.stats-summary {
  padding: $space-lg;
  padding-top: $space-xl;
}

.stats-summary-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 $space-xs;
  margin-bottom: $space-sm;
}

.stats-summary-title {
  font-size: 12px;
  color: $color-olive-light;
}

.stats-empty {
  margin-top: $space-sm;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: $space-md;
}

.stats-card {
  background-color: var(--color-card, #FFFFFF);
  border-radius: $radius-card;
  padding: $space-lg;
  box-shadow: $shadow-card;
  transition: opacity 0.15s ease;
  
  &:active {
    opacity: 0.9;
  }
}

.stats-card-label {
  font-size: 12px;
  color: $color-olive-light;
  display: block;
}

.stats-card-value {
  font-size: 24px;
  font-weight: bold;
  color: $color-ink;
  display: block;
  margin-top: $space-xs;
  
  &--cost {
    color: var(--color-accent-dark, #A8B822);
  }
}

.stats-card-unit {
  font-size: 13px;
  font-weight: normal;
  color: $color-olive-light;
  margin-left: $space-xs;
}

// 体重管理
.stats-weight {
  padding: $space-lg;
  padding-top: $space-2xl;
}

.stats-weight-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 $space-xs;
  margin-bottom: $space-sm;
}

.stats-weight-title {
  font-size: 12px;
  color: $color-olive-light;
}

.stats-weight-add {
  font-size: 14px;
  color: var(--color-accent-dark, #A8B822);
  font-weight: 600;
}

.stats-weight-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: $space-md;
}

.stats-weight-card {
  background-color: var(--color-card, #FFFFFF);
  border-radius: $radius-card;
  padding: $space-md;
  text-align: center;
  box-shadow: $shadow-card;
  transition: opacity 0.15s ease;
  
  &:active {
    opacity: 0.9;
  }
}

.stats-weight-card-label {
  font-size: 11px;
  color: $color-olive-light;
  display: block;
}

.stats-weight-card-value {
  font-size: 20px;
  font-weight: bold;
  color: $color-ink;
  display: block;
  margin-top: $space-xs;
  
  &--down {
    color: var(--color-accent-dark, #A8B822);
  }
  
  &--up {
    color: #ff6467;
  }
}

.stats-weight-card-unit {
  font-size: 10px;
  color: $color-olive-light;
  display: block;
}

.stats-weight-chart {
  background-color: var(--color-card, #FFFFFF);
  border-radius: $radius-card;
  padding: $space-lg;
  margin-top: $space-md;
  box-shadow: $shadow-card;
}

.stats-weight-chart-title {
  font-size: 14px;
  font-weight: 600;
  color: $color-ink;
  display: block;
  margin-bottom: $space-md;
}

.stats-weight-empty {
  margin-top: $space-md;
}

.stats-weight-list {
  background-color: var(--color-card, #FFFFFF);
  border-radius: $radius-card;
  margin-top: $space-md;
  box-shadow: $shadow-card;
  overflow: hidden;
}

.stats-weight-item {
  display: flex;
  align-items: center;
  padding: $space-md $space-lg;
  border-bottom: 1px solid var(--color-border, #E7E9DF);
  transition: opacity 0.15s ease;
  
  &:last-child {
    border-bottom: none;
  }
  
  &:active {
    opacity: 0.9;
  }
}

.stats-weight-item-date {
  font-size: 13px;
  color: $color-olive-light;
  width: 96px;
  flex-shrink: 0;
}

.stats-weight-item-value {
  font-size: 15px;
  font-weight: bold;
  color: $color-ink;
  flex: 1;
}

.stats-weight-item-dims {
  font-size: 11px;
  color: $color-olive-light;
  margin-right: $space-sm;
}

.stats-weight-item-delete {
  font-size: 20px;
  color: $color-olive-light;
  padding: 0 $space-sm;
}

// 表单
.stats-form-title {
  font-size: 14px;
  font-weight: 600;
  color: $color-ink;
  display: block;
  margin-bottom: $space-md;
}

.stats-form-body {
  display: flex;
  flex-direction: column;
  gap: $space-md;
}

.stats-form-row {
  display: flex;
  flex-direction: column;
  gap: $space-sm;
  
  &--grid {
    flex-direction: row;
    gap: $space-md;
  }
}

.stats-form-label {
  font-size: 12px;
  color: $color-olive-light;
  display: block;
  margin-bottom: $space-xs;
}

.stats-form-input {
  background-color: #f7f7f4;
  border-radius: 12px;
  padding: $space-md;
  font-size: 14px;
  color: $color-ink;
  width: 100%;
}

.stats-form-placeholder {
  color: rgba(107, 117, 98, 0.6);
}

.stats-form-save {
  background-color: $color-olive;
  color: $color-white;
  text-align: center;
  font-size: 14px;
  font-weight: 500;
  padding: $space-md 0;
  border-radius: 9999px;
  transition: opacity 0.15s ease;
  
  &:active {
    opacity: 0.9;
  }
}
</style>
