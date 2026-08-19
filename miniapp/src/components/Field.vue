<template>
  <view class="field">
    <text v-if="label" class="field-label">{{ label }}</text>
    <textarea
      v-if="type === 'textarea'"
      class="field-input"
      maxlength="-1"
      :placeholder="placeholder"
      placeholder-class="field-placeholder"
      :value="modelValue"
      :rows="rows"
      @input="onInput"
    />
    <input
      v-else
      class="field-input"
      :type="type"
      :placeholder="placeholder"
      placeholder-class="field-placeholder"
      :value="modelValue"
      @input="onInput"
    />
  </view>
</template>

<script setup lang="ts">
defineProps<{
  /** 标签文案 */
  label?: string
  /** 输入类型 */
  type?: "text" | "textarea" | "number" | "digit"
  /** 占位文案 */
  placeholder?: string
  /** 当前值 */
  modelValue?: string
  /** textarea 行数 */
  rows?: number
}>();

const emit = defineEmits<{
  (e: "update:modelValue", value: string): void
}>();

function onInput(e: any) {
  emit("update:modelValue", e.detail.value);
}
</script>

<style scoped lang="scss">

.field {
  display: flex;
  align-items: flex-start;
  padding: $space-md $space-lg;
}

.field-label {
  width: 80px;
  flex-shrink: 0;
  padding-top: 4px;
  font-size: 14px;
  color: $color-ink;
}

.field-input {
  flex: 1;
  min-height: 80px;
  font-size: 14px;
  color: $color-ink;
  background-color: transparent;
  border: none;
}

.field-placeholder {
  color: rgba(107, 117, 98, 0.6);
}
</style>
