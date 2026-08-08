<template>
  <view class="diary-page">
    <!-- 游客空态：未登录不发请求，引导登录 -->
    <view v-if="authStore.isGuest" class="diary-empty-guide">
      <Empty icon="🔒" text="登录后即可记录与同步网球数据" button-text="去登录" @action="goMine" />
    </view>

    <!-- 已登录内容 -->
    <template v-else>
    <!-- Hero：累计时长 -->
    <view class="diary-hero">
      <!-- 装饰光晕 -->
      <view class="diary-hero-glow" />
      <!-- 装饰图标 -->
      <text class="diary-hero-icon diary-hero-icon--racket">🏸</text>
      <text class="diary-hero-icon diary-hero-icon--ball">🎾</text>
      <!-- 内容 -->
      <text class="diary-hero-slogan">ONE SWING AT A TIME</text>
      <text class="diary-hero-title">享受每一拍，进步是顺便的事</text>
      <view class="diary-hero-progress">
        <view class="diary-hero-progress-content">
          <view class="diary-hero-progress-label">
            <text class="diary-hero-progress-text">已积累</text>
            <text class="diary-hero-progress-value">
              {{ totalHours.toFixed(1) }}
              <text class="diary-hero-progress-unit">/ 10000 小时</text>
            </text>
          </view>
          <view class="diary-hero-progress-bar">
            <view class="diary-hero-progress-bar-fill" :style="{ width: `${Math.max(1, hoursPct)}%` }" />
          </view>
        </view>
        <MoneyToggle />
      </view>
    </view>

    <!-- 空态 -->
    <view v-if="!diaryStore.loading && diaryStore.diaries.length === 0" class="diary-empty">
      <Empty
        icon="🏸"
        text="还没有日记，打完球来记一笔吧"
        button-text="记录今天"
        @action="goCreate"
      />
    </view>

    <!-- 按月分组列表 -->
    <view v-else class="diary-list">
      <view v-for="group in groups" :key="group.month" class="diary-month">
        <view class="diary-month-header">
          <text class="diary-month-title">{{ monthTitle(group.month) }}</text>
          <view class="diary-month-meta">
            <text class="diary-month-count">
              {{ group.items.length }} 次
              <text v-if="monthCost(group.items) > 0" class="diary-month-cost"> · {{ fmtMoney(monthCost(group.items)) }}</text>
            </text>
            <MoneyToggle />
          </view>
        </view>
        <view class="diary-month-items">
          <view
            v-for="d in group.items"
            :key="d.id"
            class="diary-card"
            @tap="goEdit(d.id)"
          >
            <view class="diary-card-icon">
              {{ typeIcon(d.type) }}
            </view>
            <view class="diary-card-content">
              <view class="diary-card-header">
                <text class="diary-card-type">{{ d.type }}</text>
                <text class="diary-card-time">{{ d.date.slice(5) }} {{ weekdayCN(d.date) }} {{ d.time }}</text>
              </view>
              <view class="diary-card-meta">
                <text class="diary-card-duration">{{ fmtDuration(d.duration) }}</text>
                <text class="diary-card-sep">·</text>
                <text class="diary-card-intensity">{{ intensityEmoji(d.intensity) }} {{ intensityLabel(d.intensity) }}</text>
                <text class="diary-card-sep">·</text>
                <text class="diary-card-mood">{{ moodEmoji(d.mood) }}</text>
                <text v-if="costOf(d) > 0" class="diary-card-sep">·</text>
                <text v-if="costOf(d) > 0" class="diary-card-cost">{{ costText(d) }}</text>
              </view>
              <text v-if="d.notes" class="diary-card-notes">{{ d.notes }}</text>
            </view>
            <text class="diary-card-arrow">›</text>
          </view>
        </view>
      </view>
    </view>

    <!-- FAB -->
    <view class="diary-fab" @tap="goCreate">+</view>
    </template>
  </view>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { onShow } from "@dcloudio/uni-app";

import Empty from "@/components/Empty.vue";
import MoneyToggle from "@/components/MoneyToggle.vue";
import { useAuthStore, useDiaryStore } from "@/stores";
import { useSettingsStore } from "@/stores";
import { INTENSITY, MOOD, fmtDuration, fmtMoney, sumCosts, weekdayCN } from "@/utils";
import type { Diary } from "@/types";

const authStore = useAuthStore();
const diaryStore = useDiaryStore();
const settingsStore = useSettingsStore();

/** 跳转到「我的」页登录（游客空态按钮） */
function goMine() {
  uni.switchTab({ url: "/pages/mine/mine" });
}

/** 类型 emoji 图标 */
const TYPE_ICON: Record<string, string> = {
  训练: "🎯",
  比赛: "🏆",
  发球机: "⚡",
  发球练习: "🎾",
};

function typeIcon(type: string): string {
  return TYPE_ICON[type] || "🎾";
}

function intensityEmoji(v: number): string {
  return INTENSITY.find((i) => i.v === v)?.emoji || "";
}

function intensityLabel(v: number): string {
  return INTENSITY.find((i) => i.v === v)?.label || "";
}

function moodEmoji(v: number): string {
  return MOOD.find((m) => m.v === v)?.emoji || "";
}

function costOf(d: Diary): number {
  return sumCosts(d.costs);
}

function costText(d: Diary): string {
  return settingsStore.hideAmounts ? "¥**" : fmtMoney(costOf(d));
}

/** 累计训练时长（分钟） */
const totalMinutes = computed(() =>
  diaryStore.diaries.reduce((s, d) => s + (d.duration || 0), 0),
);
const totalHours = computed(() => totalMinutes.value / 60);
const hoursPct = computed(() => Math.min(100, (totalHours.value / 10000) * 100));

/** 按月分组（日期倒序） */
const groups = computed(() => {
  const map: Record<string, Diary[]> = {};
  for (const d of diaryStore.sortedDiaries) {
    const m = d.date.slice(0, 7);
    (map[m] ??= []).push(d);
  }
  return Object.keys(map)
    .sort((a, b) => b.localeCompare(a))
    .map((month) => ({ month, items: map[month] }));
});

function monthTitle(month: string): string {
  const [y, m] = month.split("-");
  return `${y} 年 ${m} 月`;
}

function monthCost(items: Diary[]): number {
  return items.reduce((s, d) => s + sumCosts(d.costs), 0);
}

function goCreate() {
  uni.navigateTo({ url: "/pages/diary/form" });
}

function goEdit(id: number) {
  uni.navigateTo({ url: `/pages/diary/form?id=${id}` });
}

onShow(() => {
  // 游客态：不发请求，清空列表并展示游客引导
  if (authStore.isGuest) {
    diaryStore.setDiaries([]);
    return;
  }
  diaryStore.fetchList();
});
</script>

<style scoped lang="scss">
@import "@/styles/tokens.scss";

.diary-page {
  background-color: $color-paper;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.diary-empty-guide {
  flex: 1;
}

// Hero
.diary-hero {
  margin: $space-xl;
  margin-bottom: $space-md;
  border-radius: $radius-hero;
  background-color: $color-olive;
  padding: $space-xl;
  overflow: hidden;
  position: relative;
}

.diary-hero-glow {
  position: absolute;
  right: -32px;
  bottom: -40px;
  width: 144px;
  height: 144px;
  border-radius: 50%;
  background-color: $color-lime;
  opacity: 0.1;
}

.diary-hero-icon {
  position: absolute;
  opacity: 0.2;
  user-select: none;
  
  &--racket {
    right: -12px;
    top: -16px;
    font-size: 48px;
    transform: rotate(12deg);
  }
  
  &--ball {
    right: 96px;
    top: 48px;
    font-size: 24px;
    opacity: 0.25;
  }
}

.diary-hero-slogan {
  color: $color-lime;
  font-size: 10px;
  font-weight: bold;
  letter-spacing: 0.25em;
  display: block;
}

.diary-hero-title {
  color: $color-white;
  font-size: 18px;
  font-weight: bold;
  display: block;
  margin-top: 4px;
}

.diary-hero-progress {
  margin-top: 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.diary-hero-progress-content {
  flex: 1;
}

.diary-hero-progress-label {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  font-size: 12px;
}

.diary-hero-progress-text {
  color: rgba(255, 255, 255, 0.6);
}

.diary-hero-progress-value {
  color: $color-lime;
  font-weight: bold;
  font-size: 13px;
}

.diary-hero-progress-unit {
  color: rgba(255, 255, 255, 0.5);
  font-weight: normal;
  font-size: 12px;
}

.diary-hero-progress-bar {
  height: 6px;
  background-color: rgba(255, 255, 255, 0.15);
  border-radius: 9999px;
  margin-top: 6px;
  overflow: hidden;
}

.diary-hero-progress-bar-fill {
  height: 100%;
  background-color: $color-lime;
  border-radius: 9999px;
  transition: width 0.3s ease;
}

// 空态
.diary-empty {
  flex: 1;
}

// 列表
.diary-list {
  padding: 0 $space-md $space-2xl;
}

.diary-month {
  margin-bottom: $space-lg;
}

.diary-month-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  padding: 0 $space-xs;
  margin-bottom: $space-sm;
}

.diary-month-title {
  font-size: 14px;
  font-weight: bold;
  color: $color-olive-light;
}

.diary-month-meta {
  display: flex;
  align-items: center;
  gap: $space-sm;
}

.diary-month-count {
  font-size: 12px;
  color: $color-olive-light;
}

.diary-month-cost {
  color: $color-olive-light;
}

.diary-month-items {
  display: flex;
  flex-direction: column;
  gap: $space-md;
}

// 卡片
.diary-card {
  background-color: $color-white;
  border-radius: $radius-card;
  padding: $space-md;
  box-shadow: $shadow-card;
  display: flex;
  align-items: flex-start;
  gap: $space-md;
  transition: opacity 0.15s ease;
  
  &:active {
    opacity: 0.9;
  }
}

.diary-card-icon {
  width: 44px;
  height: 44px;
  border-radius: 16px;
  background-color: $color-lime-soft;
  color: $color-lime-dark;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  flex-shrink: 0;
}

.diary-card-content {
  flex: 1;
  min-width: 0;
}

.diary-card-header {
  display: flex;
  align-items: center;
  gap: $space-sm;
}

.diary-card-type {
  font-size: 15px;
  font-weight: 600;
  color: $color-ink;
}

.diary-card-time {
  font-size: 12px;
  color: $color-olive-light;
}

.diary-card-meta {
  display: flex;
  align-items: center;
  gap: $space-sm;
  margin-top: 4px;
  font-size: 12px;
  color: $color-olive-light;
  flex-wrap: wrap;
}

.diary-card-sep {
  color: $color-olive-light;
}

.diary-card-cost {
  color: $color-lime-dark;
  font-weight: 600;
}

.diary-card-notes {
  display: block;
  font-size: 12px;
  color: $color-olive-light;
  margin-top: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.diary-card-arrow {
  color: $color-olive-light;
  font-size: 16px;
  flex-shrink: 0;
}

// FAB
.diary-fab {
  position: fixed;
  right: $space-lg;
  bottom: $space-2xl;
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background-color: $color-lime;
  color: $color-ink;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  font-weight: bold;
  box-shadow: $shadow-fab;
  z-index: 20;
  transition: opacity 0.15s ease;
  
  &:active {
    opacity: 0.9;
  }
}
</style>
