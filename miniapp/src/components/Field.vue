<template>
  <view class="flex items-start px-4 py-3">
    <text v-if="label" class="w-20 shrink-0 pt-1 text-sm text-olive">{{ label }}</text>
    <textarea
      v-if="type === 'textarea'"
      class="flex-1 min-h-20 text-sm text-olive leading-relaxed"
      :placeholder="placeholder"
      :maxlength="maxlength"
      :value="modelValue"
      placeholder-class="text-olive-light/60"
      @input="onInput"
    />
    <input
      v-else
      class="flex-1 text-sm text-olive"
      :type="inputType"
      :placeholder="placeholder"
      :maxlength="maxlength"
      :value="modelValue"
      placeholder-class="text-olive-light/60"
      @input="onInput"
    />
  </view>
</template>

<script setup lang="ts">
import { computed } from "vue";

const props = withDefaults(
  defineProps<{
    /** 左侧标签 */
    label?: string
    /** 当前值 */
    modelValue: string
    /** 输入类型 */
    type?: "text" | "textarea" | "number" | "digit"
    /** 占位提示 */
    placeholder?: string
    /** 最大长度 */
    maxlength?: number
  }>(),
  {
    label: "",
    type: "text",
    placeholder: "",
    maxlength: 140,
  },
);

const emit = defineEmits<{
  (e: "update:modelValue", value: string): void
}>();

/** 小程序 input 原生 type：number 用 digit（小数键盘） */
const inputType = computed(() => (props.type === "number" ? "digit" : props.type));

/** 输入事件：透传 detail.value 给 v-model（参数用 any 兼容 uni 事件类型差异） */
function onInput(e: any) {
  emit("update:modelValue", e?.detail?.value ?? "");
}
</script>
