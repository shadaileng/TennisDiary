<template>
  <page-meta :page-style="themeStyle" :background-color="themeBg" />
  <view class="gear-page">
    <!-- 游客空态：未登录不发请求，引导登录 -->
    <view v-if="authStore.isGuest" class="gear-empty-guide">
      <Empty icon="🔒" text="登录后即可管理装备库" button-text="去登录" @action="goMine" />
    </view>

    <!-- 已登录内容 -->
    <template v-else>
    <!-- Sticky 容器：Hero + 筛选栏 -->
    <view class="gear-sticky">
      <!-- Hero：装备投入 -->
      <view class="gear-hero">
        <!-- 装饰光晕 -->
        <view class="gear-hero-glow" />
        <!-- 装饰图标 -->
        <text class="gear-hero-icon">👕</text>
        <text class="gear-hero-slogan">MY TENNIS CLOSET</text>
        <view class="gear-hero-content">
          <view class="gear-hero-stats">
            <view>
              <text class="gear-hero-stats-label">{{ totalLabel }}</text>
              <text class="gear-hero-stats-value">{{ totalText }}</text>
            </view>
            <MoneyToggle />
          </view>
          <text class="gear-hero-count">{{ filtered.length }} 件装备</text>
        </view>
      </view>

      <!-- 筛选 chips -->
      <view v-if="gearStore.gears.length > 0" class="gear-filters">
        <scroll-view scroll-x class="gear-filter-row">
          <view class="gear-filter-chips">
            <view
              v-for="c in catOptions"
              :key="c"
              class="gear-filter-chip"
              :class="catFilter === c ? 'gear-filter-chip--active' : ''"
              @tap="catFilter = c"
            >{{ c }}</view>
          </view>
        </scroll-view>
        <scroll-view scroll-x class="gear-filter-row">
          <view class="gear-filter-chips">
            <view
              v-for="mo in monthOptions"
              :key="mo"
              class="gear-filter-chip"
              :class="monthFilter === mo ? 'gear-filter-chip--active-month' : ''"
              @tap="monthFilter = mo"
            >{{ mo === "全部" ? "全部月份" : mo.replace("-", "/") }}</view>
          </view>
        </scroll-view>
      </view>
    </view>

    <!-- 空态 -->
    <view v-if="!gearStore.loading && gearStore.gears.length === 0" class="gear-empty">
      <Empty icon="🎒" text="还没有装备记录，点右下角添加" button-text="添加装备" @action="goCreate" />
    </view>
    <view v-else-if="!gearStore.loading && filtered.length === 0" class="gear-empty">
      <Empty icon="🔍" text="该筛选条件下没有装备" button-text="清除筛选" @action="clearFilter" />
    </view>

    <!-- 画报卡片流 -->
    <view v-else class="gear-grid">
      <view
        v-for="g in filtered"
        :key="g.id"
        class="gear-card"
        @tap="goEdit(g.id)"
      >
        <!-- 照片封面 / 无照片渐变 -->
        <image
          v-if="g.photo"
          :src="g.photo"
          mode="aspectFill"
          class="gear-card-image"
        />
        <view v-else class="gear-card-placeholder" :style="noPhotoBg">
          <text class="gear-card-placeholder-icon">{{ catIcon(g.category) }}</text>
        </view>

        <text class="gear-card-category">{{ g.category }}</text>

        <view class="gear-card-footer">
          <text class="gear-card-name">{{ g.name }}</text>
          <view class="gear-card-meta">
            <text class="gear-card-date">{{ g.buy_date }}</text>
            <text v-if="g.price > 0" class="gear-card-price">{{ priceText(g) }}</text>
          </view>
        </view>
      </view>
    </view>

    <!-- FAB -->
    <view class="gear-fab" @tap="goCreate">+</view>
    </template>
  </view>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { onShow } from "@dcloudio/uni-app";

import Empty from "@/components/Empty.vue";
import MoneyToggle from "@/components/MoneyToggle.vue";
import { useThemeStyle } from "@/composables/useTheme";
import { useAuthStore, useGearStore } from "@/stores";
import { useSettingsStore } from "@/stores";
import { GEAR_CATEGORIES, fmtMoney } from "@/utils";
import type { Gear } from "@/types";

const authStore = useAuthStore();
const gearStore = useGearStore();
const settingsStore = useSettingsStore();
const { themeStyle, themeBg } = useThemeStyle();

/** 跳转到「我的」页登录（游客空态按钮） */
function goMine() {
  uni.switchTab({ url: "/pages/mine/mine" });
}

const catFilter = ref("全部");
const monthFilter = ref("全部");

/** 无照片封面渐变背景（跟随球场主题深色大卡色） */
const noPhotoBg = computed(() => ({
  background: `linear-gradient(135deg, ${settingsStore.themePalette.heroB}, ${settingsStore.themePalette.heroA})`,
}));

/** 分类 emoji 图标 */
const CAT_ICON: Record<string, string> = {
  球拍: "🎾",
  球鞋: "👟",
  衣服: "👕",
  袜子: "🧦",
  帽子: "🧢",
  毛巾: "🧻",
  网球: "⚾",
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

<style scoped lang="scss">

.gear-page {
  background-color: var(--color-page-bg, #F2F2EF);
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.gear-empty-guide {
  flex: 1;
}

// Sticky 容器
.gear-sticky {
  position: sticky;
  top: 0;
  z-index: 10;
  background-color: var(--color-page-bg, #F2F2EF);
}

// Hero
.gear-hero {
  margin: $space-xl;
  margin-bottom: $space-md;
  border-radius: $radius-hero;
  background: linear-gradient(135deg, var(--color-hero-a, #242b1f), var(--color-hero-b, #3a4433));
  padding: $space-xl;
  overflow: hidden;
  position: relative;
}

.gear-hero-glow {
  position: absolute;
  right: -32px;
  bottom: -40px;
  width: 144px;
  height: 144px;
  border-radius: 50%;
  background-color: var(--color-accent, #C8DA2B);
  opacity: 0.1;
}

.gear-hero-icon {
  position: absolute;
  right: -8px;
  top: -12px;
  font-size: 40px;
  opacity: 0.2;
  transform: rotate(12deg);
  user-select: none;
}

.gear-hero-slogan {
  color: var(--color-accent, #C8DA2B);
  font-size: 10px;
  font-weight: bold;
  letter-spacing: 0.25em;
  display: block;
}

.gear-hero-content {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  margin-top: 6px;
}

.gear-hero-stats {
  display: flex;
  align-items: center;
  gap: $space-sm;
}

.gear-hero-stats-label {
  color: rgba(255, 255, 255, 0.6);
  font-size: 12px;
  display: block;
}

.gear-hero-stats-value {
  color: $color-white;
  font-size: 26px;
  font-weight: bold;
  display: block;
  margin-top: 2px;
}

.gear-hero-count {
  background-color: rgba(255, 255, 255, 0.1);
  color: $color-white;
  font-size: 12px;
  border-radius: 9999px;
  padding: $space-sm $space-md;
  margin-bottom: $space-sm;
}

// 筛选
.gear-filters {
  padding: 0 $space-md;
  display: flex;
  flex-direction: column;
  gap: $space-sm;
  margin-bottom: $space-md;
}

.gear-filter-row {
  width: 100%;
  white-space: nowrap;
}

.gear-filter-chips {
  display: inline-flex;
  gap: $space-sm;
  padding: $space-xs 0;
}

.gear-filter-chip {
  display: inline-block;
  flex-shrink: 0;
  border-radius: 9999px;
  padding: $space-sm $space-md;
  font-size: 12px;
  font-weight: 500;
  transition: opacity 0.15s ease;
  background-color: var(--color-card, #FFFFFF);
  color: $color-olive-light;
  border: 1px solid var(--color-border, #E7E9DF);
  
  &--active {
    background-color: var(--color-accent, #C8DA2B);
    color: $color-olive;
  }
  
  &--active-month {
    background-color: $color-olive;
    color: var(--color-accent, #C8DA2B);
  }
  
  &:active {
    opacity: 0.8;
  }
}

// 空态
.gear-empty {
  flex: 1;
}

// 网格
.gear-grid {
  padding: 0 $space-md $space-2xl;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: $space-md;
}

// 卡片
.gear-card {
  position: relative;
  border-radius: $radius-hero;
  overflow: hidden;
  aspect-ratio: 3/4;
  box-shadow: $shadow-card-md;
  transition: opacity 0.15s ease;
  
  &:active {
    opacity: 0.9;
  }
}

.gear-card-image {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}

.gear-card-placeholder {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.gear-card-placeholder-icon {
  font-size: 36px;
  opacity: 0.6;
}

.gear-card-category {
  position: absolute;
  top: $space-sm;
  left: $space-sm;
  background-color: var(--color-accent, #C8DA2B);
  color: $color-olive;
  font-size: 11px;
  font-weight: bold;
  border-radius: 9999px;
  padding: $space-xs $space-sm;
}

.gear-card-footer {
  position: absolute;
  left: $space-md;
  right: $space-md;
  bottom: $space-md;
  padding: $space-lg $space-md $space-md;
  background: linear-gradient(to top, rgba(23, 27, 20, 0.85), rgba(23, 27, 20, 0.4), transparent);
}

.gear-card-name {
  color: $color-white;
  font-size: 14px;
  font-weight: 600;
  line-height: 1.3;
  display: block;
}

.gear-card-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: $space-sm;
}

.gear-card-date {
  color: rgba(255, 255, 255, 0.6);
  font-size: 11px;
}

.gear-card-price {
  color: var(--color-accent, #C8DA2B);
  font-size: 14px;
  font-weight: bold;
}

// FAB
.gear-fab {
  position: fixed;
  right: $space-lg;
  bottom: $space-2xl;
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background-color: var(--color-accent, #C8DA2B);
  color: $color-ink;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  font-weight: bold;
  box-shadow: $shadow-fab;
  z-index: 20;
  transition: opacity 0.15s ease;
  
  &:active {
    opacity: 0.9;
  }
}
</style>
