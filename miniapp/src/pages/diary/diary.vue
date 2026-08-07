<template>
  <view class="page bg-paper min-h-screen flex flex-col">
    <!-- Hero：累计时长 -->
    <view class="m-4 mb-2 rounded-hero bg-olive p-5 overflow-hidden relative">
      <text class="block text-lime text-[10px] font-bold tracking-[0.25em]">ONE SWING AT A TIME</text>
      <text class="block text-white text-lg font-bold mt-1">享受每一拍，进步是顺便的事</text>
      <view class="mt-4">
        <view class="flex items-baseline justify-between text-xs">
          <text class="text-white/60">已积累</text>
          <text class="text-lime font-bold">
            {{ totalHours.toFixed(1) }}
            <text class="text-white/50 font-normal">/ 10000 小时</text>
          </text>
        </view>
        <view class="h-1.5 bg-white/15 rounded-full mt-1.5 overflow-hidden">
          <view class="h-full bg-lime rounded-full" :style="{ width: `${Math.max(1, hoursPct)}%` }" />
        </view>
      </view>
    </view>

    <!-- 空态 -->
    <view v-if="!diaryStore.loading && diaryStore.diaries.length === 0" class="flex-1">
      <Empty
        icon="🏸"
        text="还没有日记，打完球来记一笔吧"
        button-text="记录今天"
        @action="goCreate"
      />
    </view>

    <!-- 按月分组列表 -->
    <view v-else class="px-4 pb-28">
      <view v-for="group in groups" :key="group.month" class="mb-4">
        <view class="flex items-baseline justify-between px-1 mb-2">
          <text class="text-sm font-bold text-olive-light">{{ monthTitle(group.month) }}</text>
          <text class="text-xs text-olive-light">
            {{ group.items.length }} 次
            <text v-if="monthCost(group.items) > 0"> · {{ fmtMoney(monthCost(group.items)) }}</text>
          </text>
        </view>
        <view class="space-y-2.5">
          <view
            v-for="d in group.items"
            :key="d.id"
            class="card bg-white rounded-card p-3.5 active:opacity-90"
            @tap="goEdit(d.id)"
          >
            <view class="flex items-center gap-3">
              <view class="w-11 h-11 rounded-2xl bg-lime-soft text-lime-dark flex items-center justify-center text-xl shrink-0">
                {{ typeIcon(d.type) }}
              </view>
              <view class="flex-1 min-w-0">
                <view class="flex items-center gap-2">
                  <text class="font-semibold text-olive">{{ d.type }}</text>
                  <text class="text-xs text-olive-light">{{ d.date.slice(5) }} {{ weekdayCN(d.date) }} {{ d.time }}</text>
                </view>
                <view class="flex items-center gap-2 mt-1 text-xs text-olive-light flex-wrap">
                  <text>{{ fmtDuration(d.duration) }}</text>
                  <text>·</text>
                  <text>{{ intensityEmoji(d.intensity) }} {{ intensityLabel(d.intensity) }}</text>
                  <text>·</text>
                  <text>{{ moodEmoji(d.mood) }}</text>
                  <text v-if="costOf(d) > 0">·</text>
                  <text v-if="costOf(d) > 0" class="text-lime-dark font-semibold">{{ costText(d) }}</text>
                </view>
                <text v-if="d.notes" class="block text-xs text-olive-light mt-1 truncate">{{ d.notes }}</text>
              </view>
              <text class="text-olive-light text-sm shrink-0">›</text>
            </view>
          </view>
        </view>
      </view>
    </view>

    <!-- FAB -->
    <view
      class="fixed right-5 bottom-28 w-14 h-14 rounded-full bg-lime-dark text-white flex items-center justify-center text-3xl shadow-lg press-btn z-20"
      @tap="goCreate"
    >+</view>
  </view>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { onShow } from "@dcloudio/uni-app";

import { Empty } from "@/components";
import { useDiaryStore } from "@/stores";
import { useSettingsStore } from "@/stores";
import { INTENSITY, MOOD, fmtDuration, fmtMoney, sumCosts, weekdayCN } from "@/utils";
import type { Diary } from "@/types";

const diaryStore = useDiaryStore();
const settingsStore = useSettingsStore();

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
  diaryStore.fetchList();
});
</script>

<style scoped>
.press-btn:active {
  opacity: 0.9;
}
.card:active {
  transform: scale(0.99);
}
</style>
