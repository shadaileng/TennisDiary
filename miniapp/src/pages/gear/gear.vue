<template>
  <view class="page bg-paper min-h-screen flex flex-col">
    <!-- 游客空态：未登录不发请求，引导登录 -->
    <view v-if="authStore.isGuest" class="flex-1">
      <Empty icon="🔒" text="登录后即可管理装备库" button-text="去登录" @action="goMine" />
    </view>

    <!-- 已登录内容 -->
    <template v-else>
    <!-- Hero：装备投入 -->
    <view class="m-4 mb-2 rounded-hero bg-olive p-5 overflow-hidden relative">
      <text class="block text-lime text-[10px] font-bold tracking-[0.25em]">MY TENNIS CLOSET</text>
      <view class="flex items-end justify-between mt-1.5">
        <view>
          <text class="block text-white/60 text-xs">{{ totalLabel }}</text>
          <text class="block text-white text-[26px] font-bold">{{ totalText }}</text>
        </view>
        <text class="bg-white/10 text-white text-xs rounded-full px-3 py-1.5 mb-1">{{ filtered.length }} 件装备</text>
      </view>
    </view>

    <!-- 筛选 chips -->
    <view v-if="gearStore.gears.length > 0" class="px-4 space-y-1.5 mb-1">
      <scroll-view scroll-x class="w-full whitespace-nowrap">
        <view class="inline-flex gap-1.5 py-0.5">
          <view
            v-for="c in catOptions"
            :key="c"
            class="inline-block shrink-0 rounded-full px-3 py-1.5 text-xs font-medium transition-colors"
            :class="catFilter === c ? 'bg-lime text-olive' : 'bg-white text-olive-light border border-paper'"
            @tap="catFilter = c"
          >{{ c }}</view>
        </view>
      </scroll-view>
      <scroll-view scroll-x class="w-full whitespace-nowrap">
        <view class="inline-flex gap-1.5 py-0.5">
          <view
            v-for="mo in monthOptions"
            :key="mo"
            class="inline-block shrink-0 rounded-full px-3 py-1.5 text-xs font-medium transition-colors"
            :class="monthFilter === mo ? 'bg-olive text-lime' : 'bg-white text-olive-light border border-paper'"
            @tap="monthFilter = mo"
          >{{ mo === "全部" ? "全部月份" : mo.replace("-", "/") }}</view>
        </view>
      </scroll-view>
    </view>

    <!-- 空态 -->
    <view v-if="!gearStore.loading && gearStore.gears.length === 0" class="flex-1">
      <Empty icon="🎒" text="还没有装备记录，点右下角添加" button-text="添加装备" @action="goCreate" />
    </view>
    <view v-else-if="!gearStore.loading && filtered.length === 0" class="flex-1">
      <Empty icon="🔍" text="该筛选条件下没有装备" button-text="清除筛选" @action="clearFilter" />
    </view>

    <!-- 画报卡片流 -->
    <view v-else class="px-4 pb-28">
      <view class="grid grid-cols-2 gap-3">
        <view
          v-for="g in filtered"
          :key="g.id"
          class="relative rounded-hero overflow-hidden aspect-[3/4] active:opacity-90"
          @tap="goEdit(g.id)"
        >
          <!-- 照片封面 / 无照片渐变 -->
          <image
            v-if="g.photo"
            :src="g.photo"
            mode="aspectFill"
            class="absolute inset-0 w-full h-full"
          />
          <view v-else class="absolute inset-0 flex items-center justify-center" :style="noPhotoBg">
            <text class="text-4xl opacity-60">{{ catIcon(g.category) }}</text>
          </view>

          <text class="absolute top-2.5 left-2.5 bg-lime text-olive text-[11px] font-bold rounded-full px-2.5 py-1">
            {{ g.category }}
          </text>

          <view class="absolute inset-x-0 bottom-0 px-3 pb-3 pt-10" style="background: linear-gradient(to top, rgba(23,27,20,0.85), rgba(23,27,20,0.4), transparent)">
            <text class="block text-white text-sm font-semibold leading-snug">{{ g.name }}</text>
            <view class="flex items-center justify-between mt-1.5">
              <text class="text-white/60 text-[11px]">{{ g.buy_date }}</text>
              <text v-if="g.price > 0" class="text-lime text-sm font-bold">{{ priceText(g) }}</text>
            </view>
          </view>
        </view>
      </view>
    </view>

    <!-- FAB -->
    <view
      class="fixed right-5 bottom-28 w-14 h-14 rounded-full bg-lime-dark text-white flex items-center justify-center text-3xl shadow-lg press-btn z-20"
      @tap="goCreate"
    >+</view>
    </template>
  </view>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { onShow } from "@dcloudio/uni-app";

import Empty from "@/components/Empty.vue";
import { useAuthStore, useGearStore } from "@/stores";
import { useSettingsStore } from "@/stores";
import { GEAR_CATEGORIES, fmtMoney } from "@/utils";
import type { Gear } from "@/types";

const authStore = useAuthStore();
const gearStore = useGearStore();
const settingsStore = useSettingsStore();

/** 跳转到「我的」页登录（游客空态按钮） */
function goMine() {
  uni.switchTab({ url: "/pages/mine/mine" });
}

const catFilter = ref("全部");
const monthFilter = ref("全部");

/** 无照片封面渐变背景 */
const noPhotoBg = {
  background: "linear-gradient(135deg, #3A4433, #242B1F)",
};

/** 分类 emoji 图标 */
const CAT_ICON: Record<string, string> = {
  球拍: "🏸",
  球鞋: "👟",
  衣服: "👕",
  袜子: "🧦",
  帽子: "🧢",
  毛巾: "🧻",
  网球: "🎾",
  其他: "📦",
};

function catIcon(category: string): string {
  return CAT_ICON[category] || "📦";
}

/** 分类筛选选项：全部 + 已有分类 */
const catOptions = computed(() => [
  "全部",
  ...GEAR_CATEGORIES.filter((c) => gearStore.gears.some((g) => g.category === c)),
]);

/** 月份筛选选项：全部 + 已有月份（倒序） */
const monthOptions = computed(() => [
  "全部",
  ...Array.from(new Set(gearStore.gears.map((g) => g.buy_date.slice(0, 7)))).sort().reverse(),
]);

/** 筛选后的装备 */
const filtered = computed(() =>
  gearStore.gears.filter(
    (g) =>
      (catFilter.value === "全部" || g.category === catFilter.value) &&
      (monthFilter.value === "全部" || g.buy_date.startsWith(monthFilter.value)),
  ),
);

const isFiltering = computed(() => catFilter.value !== "全部" || monthFilter.value !== "全部");

const total = computed(() => filtered.value.reduce((s, g) => s + (g.price || 0), 0));

const totalLabel = computed(() =>
  isFiltering.value
    ? `${catFilter.value === "全部" ? "" : catFilter.value}${monthFilter.value === "全部" ? "" : ` ${monthFilter.value}`} 投入`.trim()
    : "装备总投入",
);

const totalText = computed(() => (settingsStore.hideAmounts ? "¥**" : fmtMoney(total.value)));

function priceText(g: Gear): string {
  return settingsStore.hideAmounts ? "¥**" : fmtMoney(g.price);
}

function clearFilter() {
  catFilter.value = "全部";
  monthFilter.value = "全部";
}

function goCreate() {
  uni.navigateTo({ url: "/pages/gear/form" });
}

function goEdit(id: number) {
  uni.navigateTo({ url: `/pages/gear/form?id=${id}` });
}

onShow(() => {
  // 游客态：不发请求，清空列表并展示游客引导
  if (authStore.isGuest) {
    gearStore.setGears([]);
    return;
  }
  gearStore.fetchList();
});
</script>

<style scoped>
.press-btn:active {
  opacity: 0.9;
}
.card:active {
  transform: scale(0.99);
}
</style>
