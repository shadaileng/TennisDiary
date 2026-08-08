<template>
  <view
    class="money-toggle"
    :class="settingsStore.hideAmounts ? 'money-toggle--hidden' : 'money-toggle--visible'"
    @tap="toggle"
  >
    <!-- 眼睛图标（显示金额） -->
    <svg
      v-if="!settingsStore.hideAmounts"
      class="money-toggle-icon"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round"
    >
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
    <!-- 眼睛斜线图标（隐藏金额） -->
    <svg
      v-else
      class="money-toggle-icon"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round"
    >
      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
      <line x1="1" y1="1" x2="23" y2="23" />
    </svg>
  </view>
</template>

<script setup lang="ts">
import { useSettingsStore } from "@/stores";

const settingsStore = useSettingsStore();

function toggle() {
  settingsStore.toggleHideAmounts();
}
</script>

<style scoped lang="scss">
@import "@/styles/tokens.scss";

.money-toggle {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: opacity 0.15s ease;
  
  &--visible {
    background-color: $color-paper;
    color: $color-olive-light;
  }
  
  &--hidden {
    background-color: rgba(255, 255, 255, 0.15);
    color: rgba(255, 255, 255, 0.8);
  }
  
  &:active {
    opacity: 0.6;
  }
}

.money-toggle-icon {
  width: 16px;
  height: 16px;
}
</style>
