<template>
  <view v-if="show" class="fixed inset-0 z-50">
    <!-- 遮罩 -->
    <view class="absolute inset-0 bg-black/40" @tap="$emit('update:show', false)" />
    <!-- 选项列表 -->
    <view class="absolute left-0 right-0 bottom-0 bg-white rounded-t-[20px] p-4 pb-safe">
      <text v-if="title" class="block text-center text-sm text-olive-light mb-3">{{ title }}</text>
      <view class="flex flex-col">
        <view
          v-for="(item, index) in actions"
          :key="index"
          class="py-3 text-center text-base"
          :class="index > 0 ? 'border-t border-paper' : ''"
          :style="{ color: item.color || '#242B1F' }"
          @tap="onSelect(item)"
        >
          {{ item.name }}
        </view>
      </view>
      <view
        class="mt-3 py-3 text-center text-sm text-olive-light border-t border-paper"
        @tap="$emit('update:show', false)"
      >
        取消
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
export interface ActionSheetAction {
  /** 显示文案 */
  name: string
  /** 返回值 */
  value: string | number
  /** 文字颜色 */
  color?: string
}

withDefaults(
  defineProps<{
    /** 是否显示 */
    show: boolean
    /** 选项列表 */
    actions: ActionSheetAction[]
    /** 标题 */
    title?: string
  }>(),
  {
    show: false,
    title: "",
  },
);

const emit = defineEmits<{
  (e: "update:show", value: boolean): void
  (e: "select", value: ActionSheetAction): void
}>();

function onSelect(item: ActionSheetAction) {
  emit("select", item);
  emit("update:show", false);
}
</script>
