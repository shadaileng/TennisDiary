<template>
  <view class="page bg-paper min-h-screen pb-12">
    <!-- 游客空态：未登录不发请求，引导登录 -->
    <view v-if="authStore.isGuest" class="pt-8">
      <Empty icon="🔒" text="登录后即可查看打球数据与体重趋势" button-text="去登录" @action="goMine" />
    </view>

    <!-- 已登录内容 -->
    <template v-else>
    <!-- 汇总卡片 -->
    <view class="px-4 pt-4">
      <view class="flex items-center justify-between px-1 mb-2">
        <text class="text-xs text-olive-light">数据总览</text>
        <MoneyToggle />
      </view>

      <!-- 空态：没有任何统计数据 -->
      <view v-if="!statsLoading && stats && !hasAnyData" class="mt-1">
        <Empty
          icon="📊"
          text="还没有任何打球数据，从记录第一篇日记开始吧"
          button-text="去记录"
          @action="goDiary"
        />
      </view>

      <!-- 统计卡片 -->
      <view v-else class="grid grid-cols-2 gap-3">
        <view class="card bg-white rounded-card p-4 active:opacity-90 transition-opacity">
          <text class="block text-xs text-olive-light">累计打球</text>
          <text class="block text-2xl font-bold text-olive mt-1">
            {{ stats?.total_sessions ?? 0 }}<text class="text-sm font-medium text-olive-light ml-1">次</text>
          </text>
        </view>
        <view class="card bg-white rounded-card p-4 active:opacity-90 transition-opacity">
          <text class="block text-xs text-olive-light">累计时长</text>
          <text class="block text-2xl font-bold text-olive mt-1">
            {{ fmtDuration(stats?.total_duration ?? 0) }}
          </text>
        </view>
        <view class="card bg-white rounded-card p-4 active:opacity-90 transition-opacity">
          <text class="block text-xs text-olive-light">平均强度</text>
          <text class="block text-2xl font-bold text-olive mt-1">
            {{ (stats?.avg_intensity ?? 0).toFixed(1) }}
          </text>
        </view>
        <view class="card bg-white rounded-card p-4 active:opacity-90 transition-opacity">
          <text class="block text-xs text-olive-light">平均心情</text>
          <text class="block text-2xl font-bold text-olive mt-1">
            {{ (stats?.avg_mood ?? 0).toFixed(1) }}
          </text>
        </view>
        <view class="card bg-white rounded-card p-4 active:opacity-90 transition-opacity">
          <text class="block text-xs text-olive-light">总花费</text>
          <text class="block text-2xl font-bold text-lime-dark mt-1">
            {{ costText }}
          </text>
        </view>
        <view class="card bg-white rounded-card p-4 active:opacity-90 transition-opacity">
          <text class="block text-xs text-olive-light">装备数</text>
          <text class="block text-2xl font-bold text-olive mt-1">
            {{ stats?.total_gears ?? 0 }}<text class="text-sm font-medium text-olive-light ml-1">件</text>
          </text>
        </view>
      </view>
    </view>

    <!-- 体重管理 -->
    <view class="px-4 pt-6">
      <view class="flex items-center justify-between px-1 mb-2">
        <text class="text-xs text-olive-light">体重管理</text>
        <text class="text-sm text-lime-dark font-semibold" @tap="openForm">＋ 记录</text>
      </view>

      <!-- 三格 -->
      <view class="grid grid-cols-3 gap-3">
        <view class="card bg-white rounded-card p-3 text-center active:opacity-90 transition-opacity">
          <text class="block text-[11px] text-olive-light">当前</text>
          <text class="block text-xl font-bold text-olive mt-0.5">{{ latest ? latest.weight : "—" }}</text>
          <text class="block text-[10px] text-olive-light">kg</text>
        </view>
        <view class="card bg-white rounded-card p-3 text-center active:opacity-90 transition-opacity">
          <text class="block text-[11px] text-olive-light">累计变化</text>
          <text class="block text-xl font-bold mt-0.5" :class="deltaColor">{{ deltaText }}</text>
          <text class="block text-[10px] text-olive-light">kg</text>
        </view>
        <view class="card bg-white rounded-card p-3 text-center active:opacity-90 transition-opacity">
          <text class="block text-[11px] text-olive-light">记录</text>
          <text class="block text-xl font-bold text-olive mt-0.5">{{ weightStore.weights.length }}</text>
          <text class="block text-[10px] text-olive-light">次</text>
        </view>
      </view>

      <!-- 体重趋势折线图 -->
      <view v-if="weightData.length >= 2" class="card bg-white rounded-card p-4 mt-3">
        <text class="block text-sm font-semibold text-olive mb-2">体重趋势</text>
        <LineChart :data="weightData" :height="130" color="#C8DA2B" unit="kg" />
      </view>

      <!-- 空态 -->
      <view v-if="!weightStore.loading && weightStore.weights.length === 0" class="mt-3">
        <Empty icon="⚖️" text="记录体重和三维，见证身材变化" button-text="记录第一条" @action="openForm" />
      </view>

      <!-- 历史记录 -->
      <view v-else-if="weightStore.weights.length > 0" class="card bg-white rounded-card mt-3 overflow-hidden">
        <view
          v-for="w in weightStore.sortedWeights"
          :key="w.id"
          class="flex items-center px-4 py-2.5 border-b border-paper last:border-0 active:opacity-90 transition-opacity"
        >
          <text class="text-[13px] text-olive-light w-24 shrink-0">{{ w.date }}</text>
          <text class="text-[15px] font-bold text-olive flex-1">{{ w.weight }} kg</text>
          <text v-if="w.bust || w.waist || w.hip" class="text-[11px] text-olive-light mr-2">
            {{ dimensionsText(w) }}
          </text>
          <text class="text-lg text-olive-light px-1" @tap="confirmRemove(w.id)">×</text>
        </view>
      </view>
    </view>

    <!-- 记录体重弹层 -->
    <Popup v-model:show="showForm" title="记录体重">
      <text class="block text-sm font-semibold text-olive mb-3">记录体重</text>
      <view class="space-y-3">
        <view>
          <text class="block text-xs text-olive-light mb-1.5">日期</text>
          <picker mode="date" :value="form.date" @change="onDateChange">
            <view class="field-input">{{ form.date }}</view>
          </picker>
        </view>
        <view>
          <text class="block text-xs text-olive-light mb-1.5">体重（kg）*</text>
          <input
            class="field-input w-full"
            type="digit"
            placeholder="62.5"
            placeholder-class="text-olive-light/60"
            :value="form.weight"
            @input="onWeightInput"
          />
        </view>
        <view class="grid grid-cols-3 gap-2.5">
          <view>
            <text class="block text-xs text-olive-light mb-1.5">胸围 cm</text>
            <input class="field-input w-full" type="digit" placeholder="选填" placeholder-class="text-olive-light/60" :value="form.bust" @input="onBustInput" />
          </view>
          <view>
            <text class="block text-xs text-olive-light mb-1.5">腰围 cm</text>
            <input class="field-input w-full" type="digit" placeholder="选填" placeholder-class="text-olive-light/60" :value="form.waist" @input="onWaistInput" />
          </view>
          <view>
            <text class="block text-xs text-olive-light mb-1.5">臀围 cm</text>
            <input class="field-input w-full" type="digit" placeholder="选填" placeholder-class="text-olive-light/60" :value="form.hip" @input="onHipInput" />
          </view>
        </view>
        <view class="bg-lime-dark text-white text-center text-base font-medium py-3 rounded-full press-btn" @tap="save">
          保存记录
        </view>
      </view>
    </Popup>
    </template>
  </view>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from "vue";
import { onShow } from "@dcloudio/uni-app";

import Empty from "@/components/Empty.vue";
import LineChart from "@/components/LineChart.vue";
import MoneyToggle from "@/components/MoneyToggle.vue";
import Popup from "@/components/Popup.vue";
import { useAuthStore, useSettingsStore, useWeightStore } from "@/stores";
import { getStats } from "@/services/data";
import { fmtDuration, fmtMoney, todayStr } from "@/utils";
import type { Stats, WeightRecord } from "@/types";

const authStore = useAuthStore();
const weightStore = useWeightStore();
const settingsStore = useSettingsStore();

/** 跳转到「我的」页登录（游客空态按钮） */
function goMine() {
  uni.switchTab({ url: "/pages/mine/mine" });
}

// ==================== 汇总 ====================

const stats = ref<Stats | null>(null);

/** 汇总统计加载中 */
const statsLoading = ref(false);

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
const latest = computed<WeightRecord | null>(() => {
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
  delta.value < 0 ? "text-lime-dark" : delta.value > 0 ? "text-red-400" : "text-olive",
);

/** 体重折线数据（最近 14 条，升序） */
const weightData = computed(() =>
  [...weightStore.weights]
    .sort((a, b) => a.date.localeCompare(b.date))
    .slice(-14)
    .map((w) => ({ label: w.date.slice(5), value: w.weight })),
);

function dimensionsText(w: WeightRecord): string {
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

function confirmRemove(id: number) {
  uni.showModal({
    title: "删除记录",
    content: "删除这条体重记录？",
    confirmColor: "#A8B822",
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
  // 游客态：不发请求，清空数据并展示游客引导
  if (authStore.isGuest) {
    weightStore.setWeights([]);
    stats.value = null;
    statsLoading.value = false;
    return;
  }
  weightStore.fetchList();
  statsLoading.value = true;
  getStats()
    .then((s) => {
      stats.value = s;
    })
    .catch((e) => {
      // 未登录或失败时保持空，打印错误便于排查
      console.error("[stats] 拉取统计数据失败", e);
    })
    .finally(() => {
      statsLoading.value = false;
    });
});
</script>

<style scoped>
.field-input {
  background-color: #f7f7f4;
  border-radius: 12px;
  padding: 10px 12px;
  font-size: 14px;
  color: #242b1f;
}
.press-btn:active {
  opacity: 0.9;
}
/* 极淡卡片阴影 */
.card {
  box-shadow: 0 1px 8px rgba(23, 27, 20, 0.04);
}
</style>
