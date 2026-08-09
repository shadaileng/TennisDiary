<template>
  <view class="w-full" :style="{ height: `${height}px` }">
    <svg v-if="data.length > 0" :viewBox="`0 0 ${W} ${height}`" class="w-full" preserveAspectRatio="none">
      <!-- 面积填充 -->
      <path :d="areaPath" :fill="color" opacity="0.15" />
      <!-- 折线 -->
      <path :d="linePath" fill="none" :stroke="color" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" />
      <!-- 数据点 + 数值标签 -->
      <g v-for="(p, i) in points" :key="i">
        <circle :cx="p.x" :cy="p.y" r="3" fill="#ffffff" :stroke="color" stroke-width="2" />
        <text v-if="isEdge(i)" :x="p.x" :y="p.y - 8" :fill="INK" text-anchor="middle" font-size="10" font-weight="600">
          {{ formatValue(data[i].value) }}{{ unit }}
        </text>
      </g>
      <!-- X 轴标签 -->
      <template v-if="data.length <= 8">
        <text v-for="(d, i) in data" :key="i" :x="points[i].x" :y="height - 2" :fill="'#9CA3AF'" text-anchor="middle" font-size="9">
          {{ d.label }}
        </text>
      </template>
      <template v-else>
        <text :x="points[0].x" :y="height - 2" :fill="'#9CA3AF'" text-anchor="start" font-size="9">
          {{ data[0].label }}
        </text>
        <text :x="points[points.length - 1].x" :y="height - 2" :fill="'#9CA3AF'" text-anchor="end" font-size="9">
          {{ data[data.length - 1].label }}
        </text>
      </template>
    </svg>
    <view v-else class="loading-placeholder" :style="{ height: `${height}px` }">
      <text class="loading-text">暂无数据</text>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed } from "vue";

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
const W = 320;
const padX = 10;
const padY = 18;

/** 格式化数值 */
function formatValue(v: number): string {
  const n = Number(v);
  if (Number.isInteger(n)) return String(n);
  return n.toFixed(1);
}

/** 计算数据点坐标 */
const points = computed(() => {
  const data = props.data;
  if (data.length === 0) return [];
  const vals = data.map((d) => d.value);
  const min = Math.min(...vals);
  const max = Math.max(...vals);
  const range = max - min || 1;
  const stepX = data.length > 1 ? (W - padX * 2) / (data.length - 1) : 0;
  return data.map((d, i) => ({
    x: padX + i * stepX,
    y: padY + (props.height - padY * 2) * (1 - (d.value - min) / range),
  }));
});

/** 折线路径 */
const linePath = computed(() => {
  if (points.value.length === 0) return "";
  return points.value.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');
});

/** 面积路径 */
const areaPath = computed(() => {
  if (points.value.length === 0) return "";
  const last = points.value[points.value.length - 1];
  const first = points.value[0];
  return `${linePath.value} L${last.x.toFixed(1)},${props.height - 6} L${first.x.toFixed(1)},${props.height - 6} Z`;
});

/** 判断是否为边缘点（首/尾/极值） */
function isEdge(i: number): boolean {
  const data = props.data;
  const vals = data.map((d) => d.value);
  const min = Math.min(...vals);
  const max = Math.max(...vals);
  return i === 0 || i === data.length - 1 || data[i].value === max || data[i].value === min;
}
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
