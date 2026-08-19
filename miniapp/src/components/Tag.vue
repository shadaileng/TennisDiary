<template>
  <text
    class="tag"
    :class="`tag--${color}`"
  >
    {{ text }}
  </text>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    /** 标签文案 */
    text: string
    /** 配色 */
    color?: "lime" | "olive" | "neutral"
  }>(),
  {
    color: "neutral",
  },
);
</script>

<style scoped lang="scss">

.tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 9999px;
  font-size: 12px;
  
  &--lime {
    background-color: rgba(var(--color-accent-rgb, 200, 218, 43), 0.2);
    color: var(--color-accent-dark, $color-lime-dark);
  }
  
  &--olive {
    background-color: rgba(36, 43, 31, 0.1);
    color: $color-ink;
  }
  
  &--neutral {
    background-color: var(--color-page-bg, #F2F2EF);
    color: $color-olive-light;
  }
}
</style>
