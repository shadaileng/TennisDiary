<template>
  <view class="page bg-paper min-h-screen pb-12">
    <view class="px-4 space-y-3.5 pt-4">
      <!-- 训练类型 -->
      <view class="bg-white rounded-card p-4">
        <text class="block text-sm font-semibold text-olive mb-2.5">训练类型</text>
        <Seg v-model="form.type" :options="SESSION_TYPES" />
      </view>

      <!-- 时间与时长 -->
      <view class="bg-white rounded-card p-4">
        <text class="block text-sm font-semibold text-olive mb-2.5">时间与时长</text>
        <view class="flex gap-3">
          <view class="flex-1">
            <text class="block text-xs text-olive-light mb-1.5">日期</text>
            <picker mode="date" :value="form.date" @change="onDateChange">
              <view class="field-input">{{ form.date || "选择日期" }}</view>
            </picker>
          </view>
          <view class="flex-1">
            <text class="block text-xs text-olive-light mb-1.5">开始时间</text>
            <picker mode="time" :value="form.time" @change="onTimeChange">
              <view class="field-input">{{ form.time || "选择时间" }}</view>
            </picker>
          </view>
        </view>
        <view class="mt-3">
          <text class="block text-xs text-olive-light mb-1.5">训练时长（分钟）</text>
          <view class="flex items-center gap-2">
            <input
              class="field-input flex-1"
              type="digit"
              :value="String(form.duration || '')"
              placeholder="90"
              placeholder-class="text-olive-light/60"
              @input="onDurationInput"
            />
            <view
              v-for="m in [60, 90, 120]"
              :key="m"
              class="pill px-3 py-1.5 rounded-full text-xs"
              :class="form.duration === m ? 'bg-lime-dark text-white' : 'bg-paper text-olive-light'"
              @tap="form.duration = m"
            >{{ m }}′</view>
          </view>
        </view>
      </view>

      <!-- 运动强度 -->
      <view class="bg-white rounded-card p-4">
        <text class="block text-sm font-semibold text-olive mb-2.5">运动强度</text>
        <EmojiScale v-model="form.intensity" :options="INTENSITY" />
      </view>

      <!-- 心情感受 -->
      <view class="bg-white rounded-card p-4">
        <text class="block text-sm font-semibold text-olive mb-2.5">心情感受</text>
        <EmojiScale v-model="form.mood" :options="MOOD" />
      </view>

      <!-- 花费明细 -->
      <view class="bg-white rounded-card p-4">
        <view class="flex items-center justify-between mb-2.5">
          <text class="text-sm font-semibold text-olive">花费明细</text>
          <text class="text-sm text-lime-dark font-semibold" @tap="addCost">＋ 添加</text>
        </view>
        <text v-if="form.costs.length === 0" class="block text-xs text-olive-light text-center py-2">
          如：场地费 / 教练费 / 网球
        </text>
        <view v-for="(c, i) in form.costs" :key="i" class="flex gap-2 items-center mb-2">
          <input
            class="field-input flex-1"
            placeholder="费用名目"
            placeholder-class="text-olive-light/60"
            :value="c.name"
            @input="onCostName(i, $event)"
          />
          <view class="relative w-28 shrink-0">
            <text class="absolute left-3 top-1/2 -translate-y-1/2 text-sm text-olive-light">¥</text>
            <input
              class="field-input !pl-7 w-full"
              type="digit"
              placeholder="0"
              placeholder-class="text-olive-light/60"
              :value="c.amount ? String(c.amount) : ''"
              @input="onCostAmount(i, $event)"
            />
          </view>
          <text class="text-xl text-olive-light px-1" @tap="removeCost(i)">×</text>
        </view>
        <view v-if="form.costs.length > 0" class="flex justify-between items-center mt-3 pt-3 border-t border-paper">
          <text class="text-xs text-olive-light">合计</text>
          <text class="text-base font-bold text-lime-dark">{{ costTotalText }}</text>
        </view>
      </view>

      <!-- 配套装备 -->
      <view class="bg-white rounded-card p-4">
        <view class="flex items-center justify-between mb-2.5">
          <text class="text-sm font-semibold text-olive">配套装备</text>
          <text class="text-sm text-lime-dark font-semibold" @tap="addGear">＋ 添加</text>
        </view>
        <text v-if="form.gears.length === 0" class="block text-xs text-olive-light text-center py-2">
          球馆 / 球拍 / 穿搭及使用体验
        </text>
        <view v-for="(g, i) in form.gears" :key="i" class="flex gap-2 items-start mb-2">
          <view class="flex-1 space-y-1.5">
            <input
              class="field-input w-full"
              placeholder="名称（球馆/球拍/穿搭）"
              placeholder-class="text-olive-light/60"
              :value="g.name"
              @input="onGearName(i, $event)"
            />
            <input
              class="field-input w-full"
              placeholder="本次使用体验（选填）"
              placeholder-class="text-olive-light/60"
              :value="g.feeling"
              @input="onGearFeeling(i, $event)"
            />
          </view>
          <text class="text-xl text-olive-light px-1 mt-2" @tap="removeGear(i)">×</text>
        </view>
      </view>

      <!-- 今日复盘 -->
      <view class="bg-white rounded-card p-4">
        <text class="block text-sm font-semibold text-olive mb-2.5">今日复盘</text>
        <textarea
          class="w-full min-h-24 text-sm text-olive leading-relaxed"
          placeholder="今天练了什么？手感如何？教练说了什么？"
          placeholder-class="text-olive-light/60"
          :value="form.notes"
          @input="onNotesInput"
        />
      </view>

      <!-- 保存 -->
      <view
        class="bg-lime-dark text-white text-center text-base font-medium py-3.5 rounded-full press-btn"
        @tap="save"
      >
        {{ isEditing ? "保存修改" : "保存日记" }}
      </view>

      <!-- 编辑模式：删除 -->
      <view
        v-if="isEditing"
        class="text-center text-sm text-red-500 py-3 press-btn"
        @tap="confirmRemove"
      >
        删除这篇日记
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, reactive } from "vue";
import { onLoad } from "@dcloudio/uni-app";

import EmojiScale from "@/components/EmojiScale.vue";
import Seg from "@/components/Seg.vue";
import { useDiaryStore } from "@/stores";
import { useSettingsStore } from "@/stores";
import { getDiary } from "@/services/data";
import { INTENSITY, MOOD, SESSION_TYPES, fmtMoney, nowTimeStr, sumCosts, todayStr } from "@/utils";
import type { SessionType } from "@/types";

const diaryStore = useDiaryStore();
const settingsStore = useSettingsStore();

interface CostItemInput {
  name: string
  amount: number
}

interface GearUseInput {
  name: string
  feeling: string
}

interface DiaryFormState {
  date: string
  time: string
  type: SessionType
  duration: number
  intensity: number
  mood: number
  costs: CostItemInput[]
  gears: GearUseInput[]
  notes: string
}

const form = reactive<DiaryFormState>({
  date: todayStr(),
  time: nowTimeStr(),
  type: "训练",
  duration: 90,
  intensity: 3,
  mood: 4,
  costs: [],
  gears: [],
  notes: "",
});

let editingId: number | null = null;
const isEditing = computed(() => editingId != null);

/** 是否加载中（编辑回填） */
const costTotalText = computed(() =>
  settingsStore.hideAmounts ? "¥**" : fmtMoney(sumCosts(form.costs)),
);

onLoad(async (query) => {
  const id = query?.id;
  if (!id) return;
  editingId = Number(id);
  uni.setNavigationBarTitle({ title: "编辑日记" });
  try {
    const d = await getDiary(editingId);
    form.date = d.date;
    form.time = d.time || "";
    form.type = d.type;
    form.duration = d.duration || 0;
    form.intensity = d.intensity;
    form.mood = d.mood;
    form.costs = d.costs.map((c) => ({ name: c.name, amount: c.amount }));
    form.gears = d.gears.map((g) => ({ name: g.name, feeling: g.feeling }));
    form.notes = d.notes || "";
  } catch (e) {
    uni.showToast({ title: "日记加载失败", icon: "none" });
  }
});

// ==================== 事件处理 ====================

function onDateChange(e: any) {
  form.date = e.detail.value;
}

function onTimeChange(e: any) {
  form.time = e.detail.value;
}

function onDurationInput(e: any) {
  form.duration = Number(e.detail.value) || 0;
}

function addCost() {
  form.costs.push({ name: "", amount: 0 });
}

function removeCost(i: number) {
  form.costs.splice(i, 1);
}

function onCostName(i: number, e: any) {
  form.costs[i].name = e.detail.value;
}

function onCostAmount(i: number, e: any) {
  form.costs[i].amount = Number(e.detail.value) || 0;
}

function addGear() {
  form.gears.push({ name: "", feeling: "" });
}

function removeGear(i: number) {
  form.gears.splice(i, 1);
}

function onGearName(i: number, e: any) {
  form.gears[i].name = e.detail.value;
}

function onGearFeeling(i: number, e: any) {
  form.gears[i].feeling = e.detail.value;
}

function onNotesInput(e: any) {
  form.notes = e.detail.value;
}

// ==================== 保存 / 删除 ====================

async function save() {
  if (!form.date || !form.duration) {
    uni.showToast({ title: "请填写日期和时长", icon: "none" });
    return;
  }
  const body = {
    date: form.date,
    time: form.time,
    type: form.type,
    duration: form.duration,
    intensity: form.intensity as 1 | 2 | 3 | 4 | 5,
    mood: form.mood as 1 | 2 | 3 | 4 | 5,
    costs: form.costs.filter((c) => c.name || c.amount),
    gears: form.gears.filter((g) => g.name),
    notes: form.notes.trim(),
  };
  try {
    if (isEditing.value && editingId != null) {
      await diaryStore.update(editingId, body);
    } else {
      await diaryStore.create(body);
    }
    uni.showToast({ title: isEditing.value ? "日记已更新" : "日记已保存", icon: "success" });
    setTimeout(() => uni.navigateBack(), 500);
  } catch (e) {
    const msg = e instanceof Error ? e.message : "保存失败";
    uni.showToast({ title: msg, icon: "none" });
  }
}

function confirmRemove() {
  uni.showModal({
    title: "删除日记",
    content: "确定删除这篇日记？",
    confirmColor: "#A8B822",
    success: async (res) => {
      if (!res.confirm || editingId == null) return;
      try {
        await diaryStore.remove(editingId);
        uni.showToast({ title: "已删除", icon: "success" });
        setTimeout(() => uni.navigateBack(), 500);
      } catch (e) {
        const msg = e instanceof Error ? e.message : "删除失败";
        uni.showToast({ title: msg, icon: "none" });
      }
    },
  });
}
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
.pill:active {
  opacity: 0.8;
}
</style>
