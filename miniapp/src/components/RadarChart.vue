<template>
  <view class="w-full" :style="{ height: `${height}px` }">
    <canvas
      v-if="data.length >= 3"
      type="2d"
      id="radarChart"
      class="w-full"
      :style="{ height: `${height}px` }"
    />
    <view v-else class="radar-placeholder" :style="{ height: `${height}px` }">
      <text class="radar-placeholder-text">暂无评分数据</text>
    </view>
  </view>
</template>

<script setup lang="ts">
import { getCurrentInstance, onMounted, watch } from "vue";

const instance = getCurrentInstance();

const props = withDefaults(
  defineProps<{
    data: { name: string; score: number }[]
    height?: number
    /** 强调色（跟随主题由页面传入，默认青柠） */
    color?: string
  }>(),
  {
    height: 220,
    color: "#C8DA2B",
  },
);

// 与 Web Charts.tsx Radar 一致：三档网格（0.33/0.66/1）+ 辐射线 + 分值多边形 + 顶点标签
const GRID = "#E7E9DF";
const INK = "#171B14";
const GREY = "#9CA3AF";

function draw() {
  if (!instance?.proxy) return;
  const data = props.data;
  if (data.length < 3) return;

  const query = uni.createSelectorQuery().in(instance.proxy);
  query
    .select("#radarChart")
    .fields({ node: true, size: true }, () => {})
    .exec((res) => {
      if (!res[0]?.node) return;
      const canvas = res[0].node;
      const ctx = canvas.getContext("2d");
      const dpr = uni.getSystemInfoSync().pixelRatio || 2;
      const W = res[0].width;
      const H = props.height;

      canvas.width = W * dpr;
      canvas.height = H * dpr;
      ctx.scale(dpr, dpr);
      ctx.clearRect(0, 0, W, H);

      const cx = W / 2;
      const cy = H / 2;
      const R = Math.min(W / 2, H / 2) - 42;
      if (R < 20) return;
      const n = data.length;
      const angle = (i: number) => -Math.PI / 2 + (2 * Math.PI * i) / n;
      const pt = (i: number, r: number) => ({
        x: cx + r * Math.cos(angle(i)),
        y: cy + r * Math.sin(angle(i)),
      });

      // 网格环（0.33 / 0.66 / 1）
      ctx.lineWidth = 1;
      for (const ratio of [0.33, 0.66, 1]) {
        ctx.beginPath();
        for (let i = 0; i < n; i++) {
          const p = pt(i, R * ratio);
          if (i === 0) {
            ctx.moveTo(p.x, p.y);
          } else {
            ctx.lineTo(p.x, p.y);
          }
        }
        ctx.closePath();
        ctx.strokeStyle = GRID;
        ctx.stroke();
      }

      // 辐射线
      for (let i = 0; i < n; i++) {
        const p = pt(i, R);
        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.lineTo(p.x, p.y);
        ctx.strokeStyle = GRID;
        ctx.stroke();
      }

      // 分值多边形
      ctx.beginPath();
      for (let i = 0; i < n; i++) {
        const v = Math.min(Number(data[i].score) || 0, 100) / 100;
        const p = pt(i, R * v);
        if (i === 0) {
          ctx.moveTo(p.x, p.y);
        } else {
          ctx.lineTo(p.x, p.y);
        }
      }
      ctx.closePath();
      ctx.fillStyle = props.color;
      ctx.globalAlpha = 0.35;
      ctx.fill();
      ctx.globalAlpha = 1;
      ctx.strokeStyle = props.color;
      ctx.lineWidth = 2;
      ctx.lineJoin = "round";
      ctx.stroke();

      // 顶点标签：名称 + 分值
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      for (let i = 0; i < n; i++) {
        const lp = pt(i, R + 18);
        ctx.font = "bold 11px sans-serif";
        ctx.fillStyle = GREY;
        ctx.fillText(String(data[i].name), lp.x, lp.y - 8);
        ctx.fillStyle = INK;
        ctx.fillText(String(Math.round(Number(data[i].score) || 0)), lp.x, lp.y + 7);
      }
    });
}

onMounted(() => {
  draw();
});

watch(
  () => props.data,
  draw,
  { deep: true },
);
</script>

<style scoped lang="scss">
.radar-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
}

.radar-placeholder-text {
  font-size: 12px;
  color: $color-olive-light;
}
</style>
