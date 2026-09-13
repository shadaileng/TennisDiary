<template>
  <page-meta :page-style="themeStyle" :background-color="themeBg" />
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
        />
        <image v-if="cardURL" :src="cardURL" mode="widthFix" class="card-img" />
        <text v-else class="canvas-placeholder">绘制中…</text>
      </view>

      <!-- 配文 -->
      <view class="form-card">
        <text class="card-title">✍️ 配文</text>
        <view class="style-row">
          <view
            v-for="s in CAPTION_STYLES"
            :key="s"
            class="style-pill"
            :class="{ active: style === s }"
            @tap="onStyleTap(s)"
          >{{ s }}</view>
        </view>
        <textarea
          class="caption-area"
          :value="caption"
          maxlength="-1"
          placeholder="分享文案，可编辑"
          placeholder-class="field-placeholder"
          @input="onCaptionInput"
        />
        <view class="caption-actions">
          <view class="btn-ghost press-btn" @tap="copyCaption">复制文案</view>
          <view class="btn-regenerate press-btn" :class="{ disabled: regenerating }" @tap="regenerate">
            <text>{{ regenerating ? "润色中…" : "润色文案" }}</text>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { getCurrentInstance, nextTick, ref, watch } from "vue";
import { onShow, onUnload } from "@dcloudio/uni-app";

import Seg from "@/components/Seg.vue";
import { useThemeStyle } from "@/composables/useTheme";
import { generateCaption, getAnalyses, getDiaries } from "@/services/data";
import type { Analysis, CaptionStyle, Diary } from "@/types";
import {
  drawShareCard,
  genCaption,
  measureShareCardHeight,
  SHARE_TEMPLATES,
  buildContext,
} from "@/utils/shareCanvas";
import type { ShareTemplate } from "@/utils/shareCanvas";
import { INTENSITY, MOOD, monthKey, todayStr } from "@/utils";
import { createTraceId, logError, logInfo } from "@/utils/eventLogger";
import { EV } from "@/utils/eventConstants";
import { useAuthStore } from "@/stores";
import { isRuntimePermissionDenied } from "@/utils/privacy";

const instance = getCurrentInstance();
const { themeStyle, themeBg } = useThemeStyle();
const authStore = useAuthStore();
const W = 1080;
const dpr = uni.getWindowInfo().pixelRatio || 2;

const CAPTION_STYLES: readonly CaptionStyle[] = ["活泼", "简洁", "专业"] as const;

const tpl = ref<ShareTemplate>("月度战报");
const style = ref<CaptionStyle>("活泼");
const caption = ref("");
const cardURL = ref("");
const cardSavePath = ref("");
const saving = ref(false);
const regenerating = ref(false);
/** 保存分享图超时句柄：页面卸载时需清理，避免离开后仍弹超时 toast */
let saveImageTimeout: ReturnType<typeof setTimeout> | null = null;
const diaries = ref<Diary[]>([]);
const analysis = ref<Analysis | undefined>(undefined);

function loadData() {
  return Promise.all([getDiaries(), getAnalyses()]);
}

onShow(async () => {
  const traceId = createTraceId();
  const t0 = Date.now();

  // 并行加载两个端点
  logInfo("加载日记列表开始", { guest: !authStore.token }, undefined, EV.SHARE_LOAD_DIARIES_START, traceId);
  logInfo("加载分析报告开始", { guest: !authStore.token }, undefined, EV.SHARE_LOAD_ANALYSES_START, traceId);

  const tDiaries = Date.now();
  const tAnalyses = Date.now();

  try {
    const [ds, as] = await loadData();

    // 日记列表结果
    logInfo("加载日记列表成功", {
      duration_ms: Date.now() - tDiaries, count: ds?.length,
    }, undefined, EV.SHARE_LOAD_DIARIES_SUCCESS, traceId);

    // 分析报告结果
    logInfo("加载分析报告成功", {
      duration_ms: Date.now() - tAnalyses, count: as?.items?.length,
    }, undefined, EV.SHARE_LOAD_ANALYSES_SUCCESS, traceId);

    diaries.value = ds;
    analysis.value = as.items?.[0];
    const pipe = buildContext(tpl.value, { diaries: ds, analysis: as.items?.[0] }, MOOD as never, INTENSITY as never);
    caption.value = genCaption(pipe);
    await nextTick();
    draw();
  } catch (e) {
    logError("分享数据加载失败", {
      error: (e as Error).message, total_duration_ms: Date.now() - t0,
    }, undefined, EV.SHARE_DATA_LOAD_FAILED, undefined, traceId);
    uni.showToast({ title: "数据加载失败", icon: "none" });
  }
});

function loadQrImage(node: any): Promise<CanvasImageSource> {
  return new Promise((resolve, reject) => {
    if (!node || typeof node.createImage !== "function") {
      reject(new Error("createImage unsupported"));
      return;
    }
    const img = node.createImage();
    img.onload = () => resolve(img as CanvasImageSource);
    img.onerror = () => reject(new Error("qr image load failed"));
    img.src = "/static/td-qr.png";
  });
}

function draw() {
  if (!instance?.proxy) return;
  const query = uni.createSelectorQuery().in(instance.proxy);
  query
    .select("#shareCanvas")
    .fields({ node: true, size: true }, () => {})
    .exec(async (res) => {
      const node = res[0]?.node as
        | { width: number; height: number; getContext: (t: string) => CanvasRenderingContext2D }
        | undefined;
      if (!node) return;

      const data = { diaries: diaries.value, analysis: analysis.value };
      let qrImage: CanvasImageSource | undefined;
      try {
        qrImage = await loadQrImage(node);
      } catch (e) {
        logError("分享图二维码加载失败，降级输出", { error: (e as Error).message }, undefined, EV.SHARE_QR_LOAD_FAILED, undefined, createTraceId());
      }

      const h = measureShareCardHeight(tpl.value, data, MOOD as never, INTENSITY as never, qrImage);

      node.width = W * dpr;
      node.height = h * dpr;

      const ctx = node.getContext("2d");
      ctx.scale(dpr, dpr);
      drawShareCard(ctx, tpl.value, data, MOOD as never, INTENSITY as never, qrImage);

      const opts = {
        canvas: node as never,
        success: (r: { tempFilePath: string }) => {
          cardURL.value = r.tempFilePath;
            // #ifdef MP-WEIXIN
            const fs = uni.getFileSystemManager()
            try {
              const now = new Date()
              const pad = (n: number) => (n < 10 ? `0${n}` : `${n}`)
              const dateStr = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`
              const monthStr = `${now.getFullYear()}-${pad(now.getMonth() + 1)}`
              let fileName: string
              if (tpl.value === "月度战报") {
                fileName = `网球月报-${monthStr}.png`
              } else if (tpl.value === "今日日记") {
                fileName = `网球日记-${dateStr}.png`
              } else {
                fileName = `网球技术评分-${dateStr}.png`
              }
              const savePath = `${wx.env.USER_DATA_PATH}/${fileName}`
              const data = fs.readFileSync(r.tempFilePath)
              fs.writeFileSync(savePath, data)
              cardSavePath.value = savePath
            } catch (e) {
              logError("持久路径写入失败", { error: String(e) }, undefined, EV.SHARE_PERSIST_SAVE_FAILED, undefined, createTraceId());
              // 降级使用 tempFilePath
            }
            // #endif
        },
        fail: (err: any) => {
          logError("canvasToTempFilePath 失败", { error: String(err) }, undefined, EV.SHARE_CANVAS_FAILED, undefined, createTraceId());
          cardURL.value = "";
        },
      };
      uni.canvasToTempFilePath(opts as never);
    });
}

watch(tpl, async (val) => {
  const pipe = buildContext(val, { diaries: diaries.value, analysis: analysis.value }, MOOD as never, INTENSITY as never);
  caption.value = genCaption(pipe);
  await nextTick();
  draw();
});

function onCaptionInput(e: any) {
  caption.value = e.detail.value;
}

function onStyleTap(s: CaptionStyle) {
  if (regenerating.value) return;
  style.value = s;
  regenerate();
}

async function regenerate() {
  if (regenerating.value) return;

  // ---- 空态检查：无数据时不调润色接口 ----
  if (tpl.value === "月度战报") {
    const monthDiaries = diaries.value.filter((d) => monthKey(d.date) === monthKey(todayStr()));
    if (monthDiaries.length === 0) {
      uni.showToast({ title: "还没有打卡记录，去记一篇吧～", icon: "none" });
      return;
    }
  } else if (tpl.value === "今日日记") {
    if (diaries.value.length === 0) {
      uni.showToast({ title: "还没有日记，先去记一篇吧～", icon: "none" });
      return;
    }
  } else if (tpl.value === "技术评分") {
    if (!analysis.value?.report) {
      uni.showToast({ title: "还没有分析报告，先去做一次分析吧～", icon: "none" });
      return;
    }
  }

  const traceId = createTraceId();
  regenerating.value = true;
  const originalText = caption.value;
  try {
    const res = await generateCaption(tpl.value, style.value, originalText);
    caption.value = res.caption || originalText;
    logInfo("润色分享文案", { template: tpl.value, style: style.value, text: originalText }, undefined, EV.SHARE_CAPTION_AI, traceId);
    uni.showToast({ title: "已润色文案", icon: "none" });
  } catch (e) {
    const pipe = buildContext(tpl.value, { diaries: diaries.value, analysis: analysis.value }, MOOD as never, INTENSITY as never);
    caption.value = genCaption(pipe);
    logError("文案润色失败，降级本地模板", { error: (e as Error).message, template: tpl.value, style: style.value, text: originalText }, undefined, EV.SHARE_CAPTION_AI_FAILED, undefined, traceId);
    uni.showToast({ title: "润色失败，已用模板文案", icon: "none" });
  } finally {
    regenerating.value = false;
  }
}

function copyCaption() {
  const traceId = createTraceId();
  logInfo("复制分享文案", { }, undefined, EV.CAPTION_COPIED, traceId);
  uni.setClipboardData({
    data: caption.value,
    success: () => uni.showToast({ title: "文案已复制", icon: "success" }),
  });
}

function saveImage() {
  if (saving.value || !cardURL.value) return;
  const traceId = createTraceId();
  logInfo("保存分享图片", { template: tpl.value }, undefined, EV.SHARE_IMAGE_SAVE, traceId);
  saving.value = true;

  let saveTimedOut = false
  saveImageTimeout = setTimeout(() => {
    if (saving.value) {
      saveTimedOut = true
      saving.value = false
      uni.showToast({ title: "保存超时，请重试", icon: "none" })
    }
  }, 10000)

  uni.saveImageToPhotosAlbum({
    filePath: cardSavePath.value || cardURL.value,
    success: () => {
      if (saveTimedOut) return
      clearImageSaveTimeout()
      logInfo("分享图片保存成功", { template: tpl.value }, undefined, EV.SHARE_IMAGE_SAVED, traceId);
      uni.showToast({ title: "已保存到相册", icon: "success" })
      saving.value = false
    },
    fail: (err) => {
      if (saveTimedOut) return
      clearImageSaveTimeout()
      if (isRuntimePermissionDenied(err)) {
        logError("保存图片权限被拒绝", { error: err.errMsg, template: tpl.value }, undefined, EV.SHARE_IMAGE_DENIED, undefined, traceId);
        uni.showModal({
          title: "提示",
          content: "需要授权使用相册功能，请在设置中开启",
          confirmText: "去设置",
          success: (m) => {
            if (m.confirm) uni.openSetting();
          },
        });
      } else {
        logError("保存图片失败", { error: err.errMsg, template: tpl.value }, undefined, EV.SHARE_IMAGE_FAILED, undefined, traceId);
        uni.showToast({ title: "保存失败，请重试", icon: "none" });
      }
      saving.value = false
    },
  });
}

/** 清理保存分享图超时定时器（成功/失败/卸载均调用，幂等） */
function clearImageSaveTimeout() {
  if (saveImageTimeout) {
    clearTimeout(saveImageTimeout)
    saveImageTimeout = null
  }
}

// 页面卸载时清理未决的保存超时定时器，避免离开页面后仍弹「保存超时」toast
onUnload(() => {
  clearImageSaveTimeout()
})
</script>

<style scoped lang="scss">
.share-page {
  min-height: 100vh;
  background-color: var(--color-page-bg, #F2F2EF);
}

.share-body {
  padding: $space-lg;
  padding-top: $space-xl;
  display: flex;
  flex-direction: column;
  gap: $space-md;
}

.form-card {
  background-color: var(--color-card, #FFFFFF);
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
  background-color: var(--color-accent, #C8DA2B);
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

.style-row {
  display: flex;
  gap: $space-sm;
  margin-bottom: $space-md;
}

.style-pill {
  flex: 1;
  text-align: center;
  font-size: 13px;
  font-weight: 500;
  padding: 8px 0;
  border-radius: 9999px;
  background-color: var(--color-page-bg, #F2F2EF);
  color: $color-olive-light;
  border: 1px solid var(--color-accent-dark, #A8B822);

  &.active {
    background-color: $color-olive;
    color: $color-white;
    border-color: $color-olive;
  }
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

.btn-regenerate.disabled {
  opacity: 0.6;
}

.btn-ghost {
  background-color: var(--color-page-bg, #F2F2EF);
  color: $color-ink;
}

.btn-regenerate {
  background-color: $color-olive;
  color: $color-white;
}
</style>
