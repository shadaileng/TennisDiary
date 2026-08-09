<template>
  <view class="w-full" :style="{ height: `${height}px` }">
    <canvas
      v-if="drawable"
      type="2d"
      id="lineChart"
      class="w-full"
      :style="{ height: `${height}px` }"
    />
    <view v-else class="loading-placeholder" :style="{ height: `${height}px` }">
      <text class="loading-text">暂无数据</text>
    </view>
  </view>
</template>

<script setup lang="ts">
import { nextTick, onMounted, ref, watch } from "vue";

const props = withDefaults(
  defineProps<{
    /** 折线数据 */
    data: { label: string; value: number }[]
    /** 高度（px） */
    height?: number
    /** 折线颜色 */
    color?: string
    /** 数值单位 */
    unit?: string
  }>(),
  {
    height: 120,
    color: "#C8DA2B",
    unit: "",
  },
);

/** 主题色 */
const INK = "#171B14";
const GRID = "#E8E8E4";

const drawable = ref(false);

function formatValue(v: number): string {
  const n = Number(v);
  if (Number.isInteger(n)) return String(n);
  return n.toFixed(1);
}

function draw(canvas: any, ctx: any, W: number, H: number, dpr: number) {
  const data = props.data;
  if (data.length === 0) return;

  // 缩放坐标系
  const padX = 10;
  const padY = 18;
  const vals = data.map((d) => d.value);
  const min = Math.min(...vals);
  const max = Math.max(...vals);
  const range = max - min || 1;
  const stepX = data.length > 1 ? (W - padX * 2) / (data.length - 1) : 0;

  const pts = data.map((d, i) => ({
    x: padX + i * stepX,
    y: padY + (H - padY * 2) * (1 - (d.value - min) / range),
  }));

  ctx.clearRect(0, 0, W, H);

  // 面积填充
  ctx.beginPath();
  ctx.moveTo(pts[0].x, pts[0].y);
  for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i].x, pts[i].y);
  ctx.lineTo(pts[pts.length - 1].x, H - 6);
  ctx.lineTo(pts[0].x, H - 6);
  ctx.closePath();
  ctx.fillStyle = props.color;
  ctx.globalAlpha = 0.15;
  ctx.fill();
  ctx.globalAlpha = 1;

  // 折线
  ctx.beginPath();
  ctx.moveTo(pts[0].x, pts[0].y);
  for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i].x, pts[i].y);
  ctx.strokeStyle = props.color;
  ctx.lineWidth = 2.5;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  ctx.stroke();

  // 数据点 + 首尾/极值标签
  ctx.font = `${10 * dpr}px sans-serif`;
  ctx.textAlign = "center";
  for (let i = 0; i < pts.length; i++) {
    const p = pts[i];
    // 圆点
    ctx.beginPath();
    ctx.arc(p.x, p.y, 3 * dpr, 0, Math.PI * 2);
    ctx.fillStyle = "#ffffff";
    ctx.fill();
    ctx.strokeStyle = props.color;
    ctx.lineWidth = 2 * dpr;
    ctx.stroke();

    // 数值标签（首/尾/极值）
    const isEdge = i === 0 || i === pts.length - 1 || data[i].value === max || data[i].value === min;
    if (isEdge) {
      ctx.fillStyle = INK;
      ctx.fillText(`${formatValue(data[i].value)}${props.unit}`, p.x, p.y - 8 * dpr);
    }
  }

  // 横轴标签
  ctx.fillStyle = "#9CA3AF";
  ctx.font = `${9 * dpr}px sans-serif`;
  if (data.length <= 8) {
    data.forEach((d, i) => {
      ctx.fillText(d.label, pts[i].x, H - 2);
    });
  } else {
    ctx.textAlign = "start";
    ctx.fillText(data[0].label, pts[0].x, H - 2);
    ctx.textAlign = "end";
    ctx.fillText(data[data.length - 1].label, pts[pts.length - 1].x, H - 2);
  }
}

function render() {
  if (props.data.length === 0) {
    drawable.value = false;
    return;
  }
  drawable.value = true;
  nextTick(() => {
    nextTick(() => {
      uni
        .createSelectorQuery()
        .select("#lineChart")
        .fields({ node: true, size: true }, (info: any) => {
          if (!info?.node) return;
          const canvas = info.node;
          const ctx = canvas.getContext("2d");
          const dpr = uni.getSystemInfoSync().pixelRatio || 2;
          canvas.width = info.width * dpr;
          canvas.height = props.height * dpr;
          ctx.scale(dpr, dpr);
          draw(canvas, ctx, info.width, props.height, dpr);
        })
        .exec();
    });
  });
}

// 监听数据变化重绘
watch(() => props.data, render, { deep: true });

onMounted(() => {
  render();
});
</script>

<style scoped lang="scss">
@import "@/styles/tokens.scss";

.loading-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
}

.loading-text {
  font-size: 12px;
  color: $color-olive-light;
}
</style>
