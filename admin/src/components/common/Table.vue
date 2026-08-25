<template>
  <div class="bg-white rounded-lg shadow-md overflow-hidden">
    <table class="w-full divide-y divide-gray-200" style="table-layout: fixed">
      <thead class="bg-gray-50">
        <tr>
          <th v-if="selectable" class="px-4 py-3 w-12 text-left">
            <input
              type="checkbox"
              class="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500 cursor-pointer"
              :checked="allSelected"
              :indeterminate="someSelected && !allSelected"
              @change="toggleAll"
            />
          </th>
          <th
            v-for="column in columns"
            :key="column.key"
            :style="widthStyle(column.width)"
            :class="[
            'px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider',
            alignClass(column.align),
            column.wrap ? 'whitespace-normal' : 'whitespace-nowrap',
            column.headerClass,
          ]"
          >
            {{ column.title }}
          </th>
          <th v-if="$slots.actions" class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
            操作
          </th>
        </tr>
      </thead>
      <tbody class="bg-white divide-y divide-gray-200">
        <tr
          v-for="(row, index) in data"
          :key="row[rowKey ?? 'id'] ?? index"
          class="transition-colors"
          :class="[
            rowClickable ? 'cursor-pointer' : '',
            isSelected(row) ? 'bg-blue-50' : 'hover:bg-gray-50',
          ]"
          @click="rowClickable && emit('row-click', row)"
        >
          <td v-if="selectable" class="px-4 py-4 w-12" @click.stop>
            <input
              type="checkbox"
              class="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
              :checked="isSelected(row)"
              :disabled="!isRowSelectable(row)"
              @change="toggleRow(row)"
            />
          </td>
          <td
            v-for="column in columns"
            :key="column.key"
            :style="widthStyle(column.width)"
            :class="[
              'px-4 py-4 text-sm text-gray-900',
              column.wrap ? 'whitespace-normal break-all' : 'whitespace-nowrap',
              alignClass(column.align),
              column.className,
            ]"
          >
            <slot :name="'cell-' + column.key" :row="row" :value="row[column.key]">
              {{ row[column.key] }}
            </slot>
          </td>
          <td v-if="$slots.actions" class="px-4 py-4 whitespace-nowrap text-right text-sm font-medium" @click.stop>
            <slot name="actions" :row="row" />
          </td>
        </tr>
        <tr v-if="data.length === 0">
          <td :colspan="colspan" class="px-6 py-12 text-center text-gray-500">
            暂无数据
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, useSlots } from 'vue'

type Column = {
  key: string
  title: string
  width?: string | number
  align?: 'left' | 'center' | 'right'
  wrap?: boolean
  className?: string
  headerClass?: string
}

const props = defineProps<{
  columns: Column[]
  data: any[]
  rowClickable?: boolean
  selectable?: boolean
  rowKey?: string
  rowSelectable?: (row: any) => boolean
}>()

const emit = defineEmits<{
  (e: 'row-click', row: any): void
  (e: 'selection-change', rows: any[]): void
}>()

const slots = useSlots()
const selectedIds = ref<Set<any>>(new Set())

const colspan = computed(
  () => props.columns.length + (props.selectable ? 1 : 0) + (slots.actions ? 1 : 0),
)

const someSelected = computed(() => selectedIds.value.size > 0)
const allSelected = computed(
  () =>
    props.data.length > 0 &&
    props.data.every((r) => selectedIds.value.has(r[props.rowKey ?? 'id'])),
)

function widthStyle(width?: string | number) {
  if (width == null) return undefined
  return typeof width === 'number' ? { width: `${width}px` } : { width }
}

function alignClass(align?: 'left' | 'center' | 'right') {
  if (align === 'center') return 'text-center'
  if (align === 'right') return 'text-right'
  return 'text-left'
}

function isRowSelectable(row: any) {
  if (!props.selectable) return false
  if (props.rowSelectable) return props.rowSelectable(row)
  return true
}

function isSelected(row: any) {
  return selectedIds.value.has(row[props.rowKey ?? 'id'])
}

function emitSelection() {
  const rows = props.data.filter((r) => selectedIds.value.has(r[props.rowKey ?? 'id']))
  emit('selection-change', rows)
}

function toggleRow(row: any) {
  if (!isRowSelectable(row)) return
  const id = row[props.rowKey ?? 'id']
  if (selectedIds.value.has(id)) selectedIds.value.delete(id)
  else selectedIds.value.add(id)
  emitSelection()
}

function toggleAll() {
  const key = props.rowKey ?? 'id'
  if (allSelected.value) {
    props.data.forEach((r) => selectedIds.value.delete(r[key]))
  } else {
    props.data.forEach((r) => {
      if (isRowSelectable(r)) selectedIds.value.add(r[key])
    })
  }
  emitSelection()
}

function clearSelection() {
  selectedIds.value.clear()
  emitSelection()
}

defineExpose({ clearSelection })
</script>
