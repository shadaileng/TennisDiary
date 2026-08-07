<template>
  <text
    class="inline-block px-2 py-0.5 rounded-full text-xs"
    :class="colorClasses[color]"
  >
    {{ text }}
  </text>
</template>

<script setup lang="ts">
import { computed } from "vue";

const props = withDefaults(
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

/** 各配色 Tailwind 类 */
const colorClasses: Record<string, string> = {
  lime: "bg-lime/20 text-lime-dark",
  olive: "bg-olive/10 text-olive",
  neutral: "bg-paper text-olive-light",
};

const classes = computed(() => colorClasses[props.color]);
</script>
