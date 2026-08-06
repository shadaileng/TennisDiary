<template>
  <view class="page bg-paper min-h-screen flex flex-col">
    <!-- 顶部占位信息 -->
    <view class="flex flex-col items-center justify-center flex-1 py-10 gap-1.5">
      <text class="text-6xl leading-none">🗒️</text>
      <text class="text-lg font-semibold text-olive">日记</text>
      <text class="text-sm text-olive-light">结构化记录打球数据，开发中</text>
    </view>

    <!-- 自定义 Tab 切换（Tailwind 实现，替代 van-tabs） -->
    <view class="mx-4 mb-4 bg-white rounded-card overflow-hidden">
      <view class="flex border-b border-paper">
        <view
          v-for="tab in tabs"
          :key="tab.key"
          class="flex-1 py-3 text-center text-sm transition-colors"
          :class="activeTab === tab.key ? 'text-lime-dark font-medium border-b-2 border-lime-dark' : 'text-olive-light'"
          @tap="activeTab = tab.key"
        >
          {{ tab.title }}
        </view>
      </view>

      <!-- 自定义 Cell 列表（替代 van-cell） -->
      <view class="px-4 py-3">
        <view class="flex items-center justify-between py-3">
          <view>
            <text class="block text-sm text-olive">{{ activeContent.title }}</text>
            <text class="block text-xs text-olive-light mt-0.5">{{ activeContent.label }}</text>
          </view>
          <text class="text-olive-light">›</text>
        </view>
        <view class="flex items-center justify-between py-3 border-t border-paper">
          <view>
            <text class="block text-sm text-olive">{{ activeContent.secondary }}</text>
            <text class="block text-xs text-olive-light mt-0.5">{{ activeContent.secondaryLabel }}</text>
          </view>
          <text class="text-olive-light">›</text>
        </view>
      </view>
    </view>

    <!-- 自定义按钮（替代 van-button） -->
    <view class="mx-4 mb-6">
      <view
        class="press-btn bg-lime-dark text-white text-center text-sm font-medium py-3 rounded-full"
        @tap="handleRecord"
      >
        记录本次{{ activeTab === 'train' ? '训练' : '比赛' }}
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, computed } from "vue";

const tabs = [
  { key: "train", title: "训练" },
  { key: "match", title: "比赛" },
];

const activeTab = ref("train");

const contentMap: Record<string, { title: string; label: string; secondary: string; secondaryLabel: string }> = {
  train: {
    title: "今日训练",
    label: "已完成 1 次 · 60 分钟",
    secondary: "近 7 天",
    secondaryLabel: "累计 3 次 · 210 分钟",
  },
  match: {
    title: "最近比赛",
    label: "暂无比赛记录",
    secondary: "胜率",
    secondaryLabel: "—",
  },
};

const activeContent = computed(() => contentMap[activeTab.value]);

function handleRecord() {
  // TODO: 对接 Phase1-8 登录与日记创建接口
  uni.showToast({ title: "待接入日记创建", icon: "none" });
}
</script>

<style scoped>
.press-btn:active {
  opacity: 0.9;
}
</style>
