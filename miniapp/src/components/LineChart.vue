<template>
  <view class="w-full" :style="{ height: `${height}px` }">
    <canvas
      v-if="data.length > 0"
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
import { getCurrentInstance, onMounted, watch } from "vue";

const instance = getCurrentInstance();

const props = withDefaults(
  defineProps<{
    data: { label: string; value: number }[]
    height?: number
    color?: string
    unit?: string
  }>(),
  {
    height: 120,
    color: "#C8DA2B",
    unit: "",
  },
);

const INK = "#171B14";
const W = 320;
const padX = 10;
const padY = 18;

function formatValue(v: number): string {
  const n = Number(v);
  if (Number.isInteger(n)) return String(n);
  return n.toFixed(1);
}

function draw() {
  const data = props.data;
  if (data.length === 0) return;

  const vals = data.map((d) => d.value);
  const min = Math.min(...vals);
  const max = Math.max(...vals);
  const range = max - min || 1;
  const stepX = data.length > 1 ? (W - padX * 2) / (data.length - 1) : 0;

  const pts = data.map((d, i) => ({
    x: padX + i * stepX,
    y: padY + (props.height - padY * 2) * (1 - (d.value - min) / range),
  }));

  const query = uni.createSelectorQuery().in(instance.proxy);
  query.select("#lineChart")
    .fields({ node: true, size: true })
    .exec((res) => {
      if (!res[0]?.node) return;
      const canvas = res[0].node;
      const ctx = canvas.getContext("2d");
      const dpr = uni.getSystemInfoSync().pixelRatio || 2;
      
      canvas.width = res[0].width * dpr;
      canvas.height = props.height * dpr;
      ctx.scale(dpr, dpr);
      ctx.clearRect(0, 0, W, props.height);

      // 面积填充
      ctx.beginPath();
      ctx.moveTo(pts[0].x, pts[0].y);
      for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i].x, pts[i].y);
      ctx.lineTo(pts[pts.length - 1].x, props.height - 6);
      ctx.lineTo(pts[0].x, props.height - 6);
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

      // 数据点 + 标签
      ctx.font = "10px sans-serif";
      ctx.textAlign = "center";
      for (let i = 0; i < pts.length; i++) {
        const p = pts[i];
        ctx.beginPath();
        ctx.arc(p.x, p.y, 3, 0, Math.PI * 2);
        ctx.fillStyle = "#ffffff";
        ctx.fill();
        ctx.strokeStyle = props.color;
        ctx.lineWidth = 2;
        ctx.stroke();

        const isEdge = i === 0 || i === pts.length - 1 || data[i].value === max || data[i].value === min;
        if (isEdge) {
          ctx.fillStyle = INK;
          ctx.font = "10px sans-serif";
          ctx.fillText(`${formatValue(data[i].value)}${props.unit}`, p.x, p.y - 8);
        }
      }

      // X 轴标签
      ctx.fillStyle = "#9CA3AF";
      ctx.font = "9px sans-serif";
      if (data.length <= 8) {
        data.forEach((d, i) => {
          ctx.fillText(d.label, pts[i].x, props.height - 2);
        });
      } else {
        ctx.textAlign = "start";
        ctx.fillText(data[0].label, pts[0].x, props.height - 2);
        ctx.textAlign = "end";
        ctx.fillText(data[data.length - 1].label, pts[pts.length - 1].x, props.height - 2);
      }
    });
}

onMounted(() => {
  draw();
});

watch(() => props.data, draw, { deep: true });
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
