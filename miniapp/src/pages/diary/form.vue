<template>
  <view class="form-page">
    <view class="form-body">
      <!-- 训练类型 -->
      <view class="form-card">
        <text class="form-card-title">训练类型</text>
        <Seg v-model="form.type" :options="SESSION_TYPES" />
      </view>

      <!-- 时间与时长 -->
      <view class="form-card">
        <text class="form-card-title">时间与时长</text>
        <view class="form-row">
          <view class="form-col">
            <text class="form-label">日期</text>
            <picker mode="date" :value="form.date" @change="onDateChange">
              <view class="field-input">{{ form.date || "选择日期" }}</view>
            </picker>
          </view>
          <view class="form-col">
            <text class="form-label">开始时间</text>
            <picker mode="time" :value="form.time" @change="onTimeChange">
              <view class="field-input">{{ form.time || "选择时间" }}</view>
            </picker>
          </view>
        </view>
        <view class="form-duration">
          <text class="form-label">训练时长（分钟）</text>
          <view class="form-duration-input">
            <input
              class="field-input"
              type="digit"
              :value="String(form.duration || '')"
              placeholder="90"
              placeholder-class="field-placeholder"
              @input="onDurationInput"
            />
            <view
              v-for="m in [60, 90, 120]"
              :key="m"
              class="pill"
              :class="form.duration === m ? 'pill--active' : 'pill--inactive'"
              @tap="form.duration = m"
            >{{ m }}′</view>
          </view>
        </view>
      </view>

      <!-- 运动强度 -->
      <view class="form-card">
        <text class="form-card-title">运动强度</text>
        <EmojiScale v-model="form.intensity" :options="INTENSITY" />
      </view>

      <!-- 心情感受 -->
      <view class="form-card">
        <text class="form-card-title">心情感受</text>
        <EmojiScale v-model="form.mood" :options="MOOD" />
      </view>

      <!-- 花费明细 -->
      <view class="form-card">
        <view class="form-card-header">
          <text class="form-card-title">花费明细</text>
          <text class="form-link" @tap="addCost">＋ 添加</text>
        </view>
        <text v-if="form.costs.length === 0" class="form-hint">如：场地费 / 教练费 / 网球</text>
        <view v-for="(c, i) in form.costs" :key="i" class="form-cost-row">
          <input
            class="field-input"
            placeholder="费用名目"
            placeholder-class="field-placeholder"
            :value="c.name"
            @input="onCostName(i, $event)"
          />
          <view class="form-cost-amount">
            <text class="form-currency">¥</text>
            <input
              class="field-input"
              type="digit"
              placeholder="0"
              placeholder-class="field-placeholder"
              :value="c.amount ? String(c.amount) : ''"
              @input="onCostAmount(i, $event)"
            />
          </view>
          <text class="form-delete" @tap="removeCost(i)">×</text>
        </view>
        <view v-if="form.costs.length > 0" class="form-total">
          <text class="form-total-label">合计</text>
          <text class="form-total-value">{{ costTotalText }}</text>
        </view>
      </view>

      <!-- 配套装备 -->
      <view class="form-card">
        <view class="form-card-header">
          <text class="form-card-title">配套装备</text>
          <text class="form-link" @tap="addGear">＋ 添加</text>
        </view>
        <text v-if="form.gears.length === 0" class="form-hint">球馆 / 球拍 / 穿搭及使用体验</text>
        <view v-for="(g, i) in form.gears" :key="i" class="form-gear-row">
          <view class="form-gear-fields">
            <input
              class="field-input"
              placeholder="名称（球馆/球拍/穿搭）"
              placeholder-class="field-placeholder"
              :value="g.name"
              @input="onGearName(i, $event)"
            />
            <input
              class="field-input"
              placeholder="本次使用体验（选填）"
              placeholder-class="field-placeholder"
              :value="g.feeling"
              @input="onGearFeeling(i, $event)"
            />
          </view>
          <text class="form-delete" @tap="removeGear(i)">×</text>
        </view>
      </view>

      <!-- 今日复盘 -->
      <view class="form-card">
        <text class="form-card-title">今日复盘</text>
        <textarea
          class="form-textarea"
          placeholder="今天练了什么？手感如何？教练说了什么？"
          placeholder-class="field-placeholder"
          :value="form.notes"
          @input="onNotesInput"
        />
      </view>

      <!-- 保存按钮 -->
      <view class="form-save press-btn" @tap="save">
        {{ isEditing ? "保存修改" : "保存日记" }}
      </view>

      <!-- 删除按钮 -->
      <view
        v-if="isEditing"
        class="form-delete-btn press-btn"
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

<style scoped lang="scss">
@import "@/styles/tokens.scss";

.form-page {
  background-color: $color-paper;
  min-height: 100vh;
  padding-bottom: $space-3xl;
}

.form-body {
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

.form-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: $space-md;
}

.form-card-title {
  font-size: $font-size-base;
  font-weight: 600;
  color: $color-ink;
  display: block;
  margin-bottom: $space-md;
}

.form-row {
  display: flex;
  gap: $space-md;
}

.form-col {
  flex: 1;
}

.form-label {
  font-size: 12px;
  color: $color-olive-light;
  display: block;
  margin-bottom: $space-sm;
}

.form-field {
  margin-bottom: $space-md;
  
  &:last-child {
    margin-bottom: 0;
  }
}

.form-field-label {
  font-size: 12px;
  color: $color-olive-light;
  display: block;
  margin-bottom: $space-sm;
}

.form-duration {
  margin-top: $space-md;
}

.form-duration-input {
  display: flex;
  align-items: center;
  gap: $space-sm;
}

.field-input {
  background-color: #f7f7f4;
  border-radius: 12px;
  padding: 14px 16px;
  font-size: 14px;
  color: $color-ink;
  width: 100%;
  box-sizing: border-box;
  min-height: 48px;
  
  &.flex-1 {
    flex: 1;
  }
}

.field-placeholder {
  color: rgba(107, 117, 98, 0.6);
}

.pill {
  border-radius: 9999px;
  padding: $space-sm $space-md;
  font-size: 12px;
  transition: opacity 0.15s ease;
  
  &--active {
    background-color: $color-olive;
    color: $color-white;
    font-weight: 500;
  }
  
  &--inactive {
    background-color: $color-paper;
    color: $color-olive-light;
  }
  
  &:active {
    opacity: 0.8;
  }
}

.form-cost-row {
  display: flex;
  align-items: center;
  gap: $space-sm;
  margin-bottom: $space-sm;
}

.form-cost-amount {
  position: relative;
  width: 112px;
  flex-shrink: 0;
}

.form-currency {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 14px;
  color: $color-olive-light;
}

.form-cost-amount .field-input {
  padding-left: 28px;
}

.form-delete {
  font-size: 20px;
  color: $color-olive-light;
  padding: 0 $space-sm;
}

.form-total {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: $space-md;
  padding-top: $space-md;
  border-top: 1px solid $color-paper;
}

.form-total-label {
  font-size: 12px;
  color: $color-olive-light;
}

.form-total-value {
  font-size: 16px;
  font-weight: bold;
  color: $color-lime-dark;
}

.form-gear-row {
  display: flex;
  align-items: flex-start;
  gap: $space-sm;
  margin-bottom: $space-sm;
}

.form-gear-fields {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: $space-sm;
}

.form-textarea {
  width: 100%;
  min-height: 120px;
  font-size: 14px;
  color: $color-ink;
  line-height: 1.6;
  background-color: #f7f7f4;
  border: none;
  border-radius: 12px;
  padding: 14px 16px;
  resize: none;
  box-sizing: border-box;
}

.form-hint {
  display: block;
  font-size: 12px;
  color: $color-olive-light;
  text-align: center;
  padding: $space-md 0;
}

.form-link {
  font-size: 14px;
  color: $color-lime-dark;
  font-weight: 600;
}

.form-save {
  background-color: $color-olive;
  color: $color-white;
  text-align: center;
  font-size: 14px;
  font-weight: 500;
  padding: $space-md 0;
  border-radius: 9999px;
  margin-top: $space-md;
  transition: opacity 0.15s ease;
  
  &:active {
    opacity: 0.9;
  }
}

.form-delete-btn {
  text-align: center;
  font-size: 14px;
  color: #ff6467;
  padding: $space-md 0;
  transition: opacity 0.15s ease;
  
  &:active {
    opacity: 0.8;
  }
}

.press-btn:active {
  opacity: 0.9;
}
</style>
