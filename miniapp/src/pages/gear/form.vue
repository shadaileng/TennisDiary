<template>
  <view class="form-page">
    <view class="form-body">
      <!-- 封面照片 -->
      <view class="form-card">
        <text class="form-card-title">封面照片（可选）</text>
        <view
          class="photo-upload"
          :class="form.photo ? 'photo-upload--has-photo' : ''"
          @tap="onPickPhoto"
        >
          <image v-if="form.photo" :src="form.photo" mode="aspectFill" class="photo-upload-img" />
          <view v-else class="photo-upload-placeholder">
            <text class="photo-upload-icon">📷</text>
            <text class="photo-upload-hint">点击上传封面图</text>
          </view>
        </view>
        <text
          v-if="form.photo"
          class="photo-remove"
          @tap="form.photo = ''"
        >移除封面</text>
      </view>

      <!-- 类型 -->
      <view class="form-card">
        <text class="form-card-title">类型</text>
        <Seg v-model="form.category" :options="GEAR_CATEGORIES" />
      </view>

      <!-- 信息 -->
      <view class="form-card">
        <text class="form-card-title">信息</text>
        <view class="form-fields">
          <input
            class="field-input"
            placeholder="装备名称（如 Wilson Pro Staff）"
            placeholder-class="field-placeholder"
            :value="form.name"
            @input="onNameInput"
          />
          <view class="form-row">
            <view class="form-col">
              <text class="form-label">购入日期</text>
              <picker mode="date" :value="form.buy_date" @change="onDateChange">
                <view class="field-input">{{ form.buy_date || "选择日期" }}</view>
              </picker>
            </view>
            <view class="form-col">
              <text class="form-label">金额 ¥</text>
              <input
                class="field-input"
                type="digit"
                placeholder="0"
                placeholder-class="field-placeholder"
                :value="form.price ? String(form.price) : ''"
                @input="onPriceInput"
              />
            </view>
          </view>
          <textarea
            class="field-input field-textarea"
            placeholder="使用感受（选填）"
            placeholder-class="field-placeholder"
            :value="form.feeling"
            @input="onFeelingInput"
          />
        </view>
      </view>

      <!-- 保存按钮 -->
      <view class="form-save press-btn" @tap="save">
        {{ isEditing ? "保存修改" : "装备入库" }}
      </view>

      <!-- 删除按钮 -->
      <view
        v-if="isEditing"
        class="form-delete-btn press-btn"
        @tap="confirmRemove"
      >
        删除这件装备
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from "vue";
import { onLoad } from "@dcloudio/uni-app";

import Seg from "@/components/Seg.vue";
import { useGearStore } from "@/stores";
import { getGear } from "@/services/data";
import { GEAR_CATEGORIES, choosePhoto, safeNavigateBack, todayStr } from "@/utils";

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

let editingId = ref<number | null>(null);
const isEditing = computed(() => editingId.value != null);
const saving = ref(false);

onLoad(async (query) => {
  const id = query?.id;
  if (!id) return;
      editingId.value = Number(id);
  uni.setNavigationBarTitle({ title: "编辑装备" });
  try {
    const g = await getGear(editingId.value);
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

async function save() {
  if (saving.value) return;
  if (!form.name.trim()) {
    uni.showToast({ title: "请填写装备名称", icon: "none" });
    return;
  }
  saving.value = true;
  const body = {
    category: form.category,
    name: form.name.trim(),
    buy_date: form.buy_date,
    price: form.price || 0,
    feeling: form.feeling.trim(),
    photo: form.photo || undefined,
  };
  try {
    if (isEditing.value && editingId.value != null) {
      await gearStore.update(editingId.value, body);
    } else {
      await gearStore.create(body);
    }
    uni.showToast({ title: isEditing.value ? "已更新" : "装备已入库", icon: "success" });
    setTimeout(() => safeNavigateBack("/pages/gear/gear"), 500);
  } catch (e) {
    const msg = e instanceof Error ? e.message : "保存失败";
    uni.showToast({ title: msg, icon: "none" });
  } finally {
    saving.value = false;
  }
}

function confirmRemove() {
  uni.showModal({
    title: "删除装备",
    content: "确定删除这件装备？",
    confirmColor: "#A8B822",
    success: async (res) => {
      if (!res.confirm || editingId.value == null) return;
      try {
        await gearStore.remove(editingId.value);
        uni.showToast({ title: "已删除", icon: "success" });
        setTimeout(() => safeNavigateBack("/pages/gear/gear"), 500);
      } catch (e) {
        const msg = e instanceof Error ? e.message : "删除失败";
        uni.showToast({ title: msg, icon: "none" });
      }
    },
  });
}
</script>

<style scoped lang="scss">

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

.form-card-title {
  font-size: $font-size-base;
  font-weight: 600;
  color: $color-ink;
  display: block;
  margin-bottom: $space-md;
}

.form-fields {
  display: flex;
  flex-direction: column;
  gap: $space-md;
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

.field-input {
  background-color: #f7f7f4;
  border-radius: 12px;
  padding: 14px 16px;
  font-size: 14px;
  color: $color-ink;
  width: 100%;
  box-sizing: border-box;
  min-height: 48px;
}

.field-textarea {
  min-height: 96px;
  resize: none;
  line-height: 1.6;
  background-color: #f7f7f4;
  border-radius: 12px;
  padding: 14px 16px;
  box-sizing: border-box;
}

.field-placeholder {
  color: rgba(107, 117, 98, 0.6);
}

// 照片上传
.photo-upload {
  border-radius: 16px;
  overflow: hidden;
  border: 2px dashed $color-paper;
  transition: border-color 0.15s ease;
  cursor: pointer;
  
  &--has-photo {
    border-color: transparent;
  }
}

.photo-upload-img {
  width: 100%;
  height: 208px;
  display: block;
}

.photo-upload-placeholder {
  padding: 24px 0;
  text-align: center;
}

.photo-upload-icon {
  font-size: 24px;
  display: block;
  margin-bottom: 4px;
}

.photo-upload-hint {
  font-size: 12px;
  color: $color-olive-light;
}

.photo-remove {
  display: inline-block;
  margin-top: 8px;
  font-size: 12px;
  color: $color-olive-light;
  text-decoration: underline;
}

// 保存/删除按钮
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
