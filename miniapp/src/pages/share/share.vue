<template>
  <view class="share-page">
    <view class="share-body">
      <!-- 选择模板 -->
      <view class="form-card">
        <text class="card-title">🎨 选择模板</text>
        <Seg v-model="tpl" :options="SHARE_TEMPLATES" />
      </view>

      <!-- 卡片预览 -->
      <view class="form-card">
        <view class="preview-head">
          <text class="card-title">🖼 卡片预览</text>
          <view class="save-btn press-btn" @tap="saveImage">
            <text v-if="saving">保存中…</text>
            <text v-else>保存图片</text>
          </view>
        </view>
        <canvas
          id="shareCanvas"
          type="2d"
          class="share-canvas"
          :style="{ height: `${canvasH}px` }"
        />
        <image v-if="cardURL" :src="cardURL" mode="widthFix" class="card-img" />
        <text v-else class="canvas-placeholder">绘制中…</text>
      </view>

      <!-- 配文 -->
      <view class="form-card">
        <text class="card-title">✍️ 配文</text>
        <textarea
          class="caption-area"
          :value="caption"
          placeholder="分享文案，可编辑"
          placeholder-class="field-placeholder"
          @input="onCaptionInput"
        />
        <view class="caption-actions">
          <view class="btn-ghost press-btn" @tap="copyCaption">复制文案</view>
          <view class="btn-regenerate press-btn" @tap="regenerate">重新生成</view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { getCurrentInstance, nextTick, ref, watch } from "vue";
import { onShow } from "@dcloudio/uni-app";

import Seg from "@/components/Seg.vue";
import { getAnalyses, getDiaries } from "@/services/data";
import type { Analysis, Diary } from "@/types";
import { drawShareCard, genCaption, SHARE_TEMPLATES } from "@/utils/shareCanvas";
import type { ShareTemplate } from "@/utils/shareCanvas";
import { INTENSITY, MOOD } from "@/utils";

const instance = getCurrentInstance();
const W = 1080;
const H = 1500;
const canvasH = 300;
const dpr = uni.getSystemInfoSync().pixelRatio || 2;

const tpl = ref<ShareTemplate>("月度战报");
const caption = ref("");
const cardURL = ref("");
const saving = ref(false);
const diaries = ref<Diary[]>([]);
const analysis = ref<Analysis | undefined>(undefined);

function loadData() {
  return Promise.all([getDiaries(), getAnalyses()]);
}

onShow(async () => {
  try {
    const [ds, as] = await loadData();
    diaries.value = ds;
    analysis.value = as.items?.[0];
    caption.value = genCaption(tpl.value, { diaries: ds, analysis: as.items?.[0] });
    await nextTick();
    draw();
  } catch {
    uni.showToast({ title: "数据加载失败", icon: "none" });
  }
});

function draw() {
  if (!instance?.proxy) return;
  const query = uni.createSelectorQuery().in(instance.proxy);
  query
    .select("#shareCanvas")
    .fields({ node: true, size: true }, () => {})
    .exec((res) => {
      const node = res[0]?.node as
        | { width: number; height: number; getContext: (t: string) => CanvasRenderingContext2D }
        | undefined;
      if (!node) return;
      node.width = W * dpr;
      node.height = H * dpr;
      const ctx = node.getContext("2d");
      ctx.scale(dpr, dpr);
      drawShareCard(ctx, tpl.value, { diaries: diaries.value, analysis: analysis.value }, MOOD as never, INTENSITY as never);
      const opts = {
        canvas: node as never,
        success: (r: { tempFilePath: string }) => {
          cardURL.value = r.tempFilePath;
        },
        fail: () => {
          cardURL.value = "";
        },
      };
      uni.canvasToTempFilePath(opts as never);
    });
}

watch(tpl, async (val) => {
  caption.value = genCaption(val, { diaries: diaries.value, analysis: analysis.value });
  await nextTick();
  draw();
});

function onCaptionInput(e: any) {
  caption.value = e.detail.value;
}

function regenerate() {
  caption.value = genCaption(tpl.value, { diaries: diaries.value, analysis: analysis.value });
  uni.showToast({ title: "已重新生成", icon: "none" });
}

function copyCaption() {
  uni.setClipboardData({
    data: caption.value,
    success: () => uni.showToast({ title: "文案已复制", icon: "success" }),
  });
}

function saveImage() {
  if (saving.value || !cardURL.value) return;
  saving.value = true;
  uni.saveImageToPhotosAlbum({
    filePath: cardURL.value,
    success: () => uni.showToast({ title: "已保存到相册", icon: "success" }),
    fail: (err) => {
      if (err.errMsg?.includes("auth") || err.errMsg?.includes("denied")) {
        uni.showModal({
          title: "需要相册权限",
          content: "请在设置中允许保存图片到相册",
          confirmText: "去设置",
          success: (m) => {
            if (m.confirm) uni.openSetting();
          },
        });
      } else {
        uni.showToast({ title: "保存失败，请重试", icon: "none" });
      }
    },
    complete: () => {
      saving.value = false;
    },
  });
}
</script>

<style scoped lang="scss">
.share-page {
  min-height: 100vh;
  background-color: $color-paper;
}

.share-body {
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

.card-title {
  display: block;
  font-size: $font-size-base;
  font-weight: 600;
  color: $color-ink;
  margin-bottom: $space-md;
}

.preview-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: $space-md;

  .card-title {
    margin-bottom: 0;
  }
}

.save-btn {
  background-color: $color-lime;
  color: $color-ink;
  font-size: 13px;
  font-weight: 500;
  padding: 8px 16px;
  border-radius: 9999px;
}

.share-canvas {
  position: fixed;
  left: -9999px;
  top: 0;
  width: 100%;
}

.card-img {
  width: 100%;
  border-radius: $radius-card;
  border: 1px solid #eceae4;
}

.canvas-placeholder {
  display: block;
  text-align: center;
  padding: 60px 0;
  color: $color-olive-light;
  font-size: 13px;
}

.caption-area {
  width: 100%;
  box-sizing: border-box;
  min-height: 160px;
  background-color: #f7f7f4;
  border-radius: 16px;
  padding: 14px 16px;
  font-size: 14px;
  color: $color-ink;
  line-height: 1.6;
}

.caption-actions {
  display: flex;
  gap: $space-sm;
  margin-top: $space-md;
}

.btn-ghost,
.btn-regenerate {
  flex: 1;
  text-align: center;
  font-size: 14px;
  font-weight: 500;
  padding: 12px 0;
  border-radius: 9999px;
}

.btn-ghost {
  background-color: $color-paper;
  color: $color-ink;
}

.btn-regenerate {
  background-color: $color-olive;
  color: $color-white;
}
</style>