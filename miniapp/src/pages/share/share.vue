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
import { onShow } from "@dcloudio/uni-app";

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
import { isRuntimePermissionDenied } from "@/utils/privacy";

const instance = getCurrentInstance();
const { themeStyle, themeBg } = useThemeStyle();
const W = 1080;
const dpr = uni.getSystemInfoSync().pixelRatio || 2;

const CAPTION_STYLES: readonly CaptionStyle[] = ["活泼", "简洁", "专业"] as const;

const tpl = ref<ShareTemplate>("月度战报");
const style = ref<CaptionStyle>("活泼");
const caption = ref("");
const cardURL = ref("");
const cardSavePath = ref("");
const saving = ref(false);
const regenerating = ref(false);
const diaries = ref<Diary[]>([]);
const analysis = ref<Analysis | undefined>(undefined);

function loadData() {
  return Promise.all([getDiaries(), getAnalyses()]);
}

onShow(async () => {
  const traceId = createTraceId();
  logInfo("加载分享数据", { trace_id: traceId }, "share_data_load", traceId);
  try {
    const [ds, as] = await loadData();
    diaries.value = ds;
    analysis.value = as.items?.[0];
    const pipe = buildContext(tpl.value, { diaries: ds, analysis: as.items?.[0] }, MOOD as never, INTENSITY as never);
    caption.value = genCaption(pipe);
    await nextTick();
    draw();
  } catch (e) {
    logError("分享数据加载失败", { trace_id: traceId, error: (e as Error).message }, "share_data_load_failed", undefined, traceId);
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

      const data = { diaries: diaries.value, analysis: analysis.value };
      const h = measureShareCardHeight(tpl.value, data, MOOD as never, INTENSITY as never);

      node.width = W * dpr;
      node.height = h * dpr;

      const ctx = node.getContext("2d");
      ctx.scale(dpr, dpr);
      drawShareCard(ctx, tpl.value, data, MOOD as never, INTENSITY as never);

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
              // @ts-ignore wx is WeChat mini-program global
              const savePath = `${wx.env.USER_DATA_PATH}/${fileName}`
              const data = fs.readFileSync(r.tempFilePath)
              fs.writeFileSync(savePath, data)
              cardSavePath.value = savePath
            } catch (e) {
              logError("持久路径写入失败", { error: String(e) }, "share_persist_save_failed", undefined, createTraceId());
              console.error('[share] 持久路径写入失败:', e)
              // 降级使用 tempFilePath
            }
            // #endif
        },
        fail: (err) => {
          logError("canvasToTempFilePath 失败", { error: String(err) }, "share_canvas_failed", undefined, createTraceId());
          console.error('[share] canvasToTempFilePath fail:', err)
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
  try {
    const res = await generateCaption(tpl.value, style.value, caption.value);
    caption.value = res.caption || caption.value;
    logInfo("润色分享文案", { trace_id: traceId, template: tpl.value, style: style.value }, "share_caption_ai", traceId);
    uni.showToast({ title: "已润色文案", icon: "none" });
  } catch (e) {
    const pipe = buildContext(tpl.value, { diaries: diaries.value, analysis: analysis.value }, MOOD as never, INTENSITY as never);
    caption.value = genCaption(pipe);
    logError("文案润色失败，降级本地模板", { trace_id: traceId, error: (e as Error).message, template: tpl.value }, "share_caption_ai_failed", undefined, traceId);
    uni.showToast({ title: "润色失败，已用模板文案", icon: "none" });
  } finally {
    regenerating.value = false;
  }
}

function copyCaption() {
  const traceId = createTraceId();
  logInfo("复制分享文案", { trace_id: traceId }, "caption_copied", traceId);
  uni.setClipboardData({
    data: caption.value,
    success: () => uni.showToast({ title: "文案已复制", icon: "success" }),
  });
}

function saveImage() {
  if (saving.value || !cardURL.value) return;
  const traceId = createTraceId();
  logInfo("保存分享图片", { trace_id: traceId, template: tpl.value }, "share_image_save", traceId);
  saving.value = true;

  let saveTimedOut = false
  const saveTimeout = setTimeout(() => {
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
      clearTimeout(saveTimeout)
      logInfo("分享图片保存成功", { trace_id: traceId, template: tpl.value }, "share_image_saved", traceId);
      uni.showToast({ title: "已保存到相册", icon: "success" })
      saving.value = false
    },
    fail: (err) => {
      if (saveTimedOut) return
      clearTimeout(saveTimeout)
      if (isRuntimePermissionDenied(err)) {
        logError("保存图片权限被拒绝", { trace_id: traceId, error: err.errMsg, template: tpl.value }, "share_image_denied", undefined, traceId);
        uni.showModal({
          title: "提示",
          content: "需要授权使用相册功能，请在设置中开启",
          confirmText: "去设置",
          success: (m) => {
            if (m.confirm) uni.openSetting();
          },
        });
      } else {
        console.error('[share] saveImage fail:', err)
        logError("保存图片失败", { trace_id: traceId, error: err.errMsg, template: tpl.value }, "share_image_failed", undefined, traceId);
        uni.showToast({ title: "保存失败，请重试", icon: "none" });
      }
      saving.value = false
    },
  });
}
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
