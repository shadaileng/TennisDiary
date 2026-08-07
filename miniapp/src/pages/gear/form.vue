<template>
  <view class="page bg-paper min-h-screen pb-12">
    <view class="px-4 space-y-3.5 pt-4">
      <!-- 封面照片 -->
      <view class="bg-white rounded-card p-4">
        <text class="block text-sm font-semibold text-olive mb-2.5">封面照片（可选）</text>
        <view
          class="rounded-2xl overflow-hidden border-2 border-dashed border-paper"
          :class="form.photo ? 'border-transparent' : ''"
          @tap="onPickPhoto"
        >
          <image v-if="form.photo" :src="form.photo" mode="aspectFill" class="w-full h-52" />
          <view v-else class="py-6 text-center">
            <text class="block text-2xl mb-1">📷</text>
            <text class="text-xs text-olive-light">点击上传封面图</text>
          </view>
        </view>
        <text
          v-if="form.photo"
          class="inline-block mt-2 text-xs text-olive-light underline"
          @tap="form.photo = ''"
        >移除封面</text>
      </view>

      <!-- 类型 -->
      <view class="bg-white rounded-card p-4">
        <text class="block text-sm font-semibold text-olive mb-2.5">类型</text>
        <Seg v-model="form.category" :options="GEAR_CATEGORIES" />
      </view>

      <!-- 信息 -->
      <view class="bg-white rounded-card p-4">
        <text class="block text-sm font-semibold text-olive mb-2.5">信息</text>
        <view class="space-y-2.5">
          <input
            class="field-input w-full"
            placeholder="装备名称（如 Wilson Pro Staff）"
            placeholder-class="text-olive-light/60"
            :value="form.name"
            @input="onNameInput"
          />
          <view class="grid grid-cols-2 gap-2.5">
            <view>
              <text class="block text-xs text-olive-light mb-1.5">购入日期</text>
              <picker mode="date" :value="form.buy_date" @change="onDateChange">
                <view class="field-input">{{ form.buy_date || "选择日期" }}</view>
              </picker>
            </view>
            <view>
              <text class="block text-xs text-olive-light mb-1.5">金额 ¥</text>
              <input
                class="field-input w-full"
                type="digit"
                placeholder="0"
                placeholder-class="text-olive-light/60"
                :value="form.price ? String(form.price) : ''"
                @input="onPriceInput"
              />
            </view>
          </view>
          <textarea
            class="field-input w-full min-h-18 leading-relaxed"
            placeholder="使用感受（选填）"
            placeholder-class="text-olive-light/60"
            :value="form.feeling"
            @input="onFeelingInput"
          />
        </view>
      </view>

      <!-- 保存 -->
      <view
        class="bg-lime-dark text-white text-center text-base font-medium py-3.5 rounded-full press-btn"
        @tap="save"
      >
        {{ isEditing ? "保存修改" : "装备入库" }}
      </view>

      <!-- 编辑模式：删除 -->
      <view
        v-if="isEditing"
        class="text-center text-sm text-red-500 py-3 press-btn"
        @tap="confirmRemove"
      >
        删除这件装备
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, reactive } from "vue";
import { onLoad } from "@dcloudio/uni-app";

import Seg from "@/components/Seg.vue";
import { useGearStore } from "@/stores";
import { getGear } from "@/services/data";
import { GEAR_CATEGORIES, choosePhoto, todayStr } from "@/utils";

const gearStore = useGearStore();

interface GearFormState {
  category: string
  name: string
  buy_date: string
  price: number
  feeling: string
  photo: string
}

const form = reactive<GearFormState>({
  category: "球拍",
  name: "",
  buy_date: todayStr(),
  price: 0,
  feeling: "",
  photo: "",
});

let editingId: number | null = null;
const isEditing = computed(() => editingId != null);

onLoad(async (query) => {
  const id = query?.id;
  if (!id) return;
  editingId = Number(id);
  uni.setNavigationBarTitle({ title: "编辑装备" });
  try {
    const g = await getGear(editingId);
    form.category = g.category || "球拍";
    form.name = g.name || "";
    form.buy_date = g.buy_date || todayStr();
    form.price = g.price || 0;
    form.feeling = g.feeling || "";
    form.photo = g.photo || "";
  } catch (e) {
    uni.showToast({ title: "装备加载失败", icon: "none" });
  }
});

// ==================== 事件处理 ====================

function onNameInput(e: any) {
  form.name = e.detail.value;
}

function onDateChange(e: any) {
  form.buy_date = e.detail.value;
}

function onPriceInput(e: any) {
  form.price = Number(e.detail.value) || 0;
}

function onFeelingInput(e: any) {
  form.feeling = e.detail.value;
}

async function onPickPhoto() {
  const dataUrl = await choosePhoto(900, 0.8);
  if (dataUrl) {
    form.photo = dataUrl;
  }
}

// ==================== 保存 / 删除 ====================

async function save() {
  if (!form.name.trim()) {
    uni.showToast({ title: "请填写装备名称", icon: "none" });
    return;
  }
  const body = {
    category: form.category,
    name: form.name.trim(),
    buy_date: form.buy_date,
    price: form.price || 0,
    feeling: form.feeling.trim(),
    photo: form.photo || undefined,
  };
  try {
    if (isEditing.value && editingId != null) {
      await gearStore.update(editingId, body);
    } else {
      await gearStore.create(body);
    }
    uni.showToast({ title: isEditing.value ? "已更新" : "装备已入库", icon: "success" });
    setTimeout(() => uni.navigateBack(), 500);
  } catch (e) {
    const msg = e instanceof Error ? e.message : "保存失败";
    uni.showToast({ title: msg, icon: "none" });
  }
}

function confirmRemove() {
  uni.showModal({
    title: "删除装备",
    content: "确定删除这件装备？",
    confirmColor: "#A8B822",
    success: async (res) => {
      if (!res.confirm || editingId == null) return;
      try {
        await gearStore.remove(editingId);
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
</style>
