<template>
  <div class="bg-white rounded-lg shadow-md p-6">
    <div class="flex items-center justify-between">
      <div>
        <p class="text-sm text-gray-600">{{ title }}</p>
        <p class="text-2xl font-bold" :class="colorClass">{{ value }}</p>
      </div>
      <div class="p-3 rounded-full" :class="iconBgClass">
        <component :is="iconComponent" class="w-6 h-6" :class="iconClass" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import {
  UsersIcon,
  DocumentTextIcon,
  WrenchIcon,
  CheckCircleIcon
} from '@heroicons/vue/24/outline'

const props = defineProps<{
  title: string
  value: number
  icon: string
  color: 'blue' | 'green' | 'purple' | 'orange'
}>()

const iconMap: Record<string, typeof UsersIcon> = {
  UsersIcon,
  DocumentTextIcon,
  WrenchIcon,
  CheckCircleIcon
}

const iconComponent = computed(() => iconMap[props.icon] || UsersIcon)

const colorMap = {
  blue: {
    text: 'text-blue-600',
    bg: 'bg-blue-100',
    icon: 'text-blue-600'
  },
  green: {
    text: 'text-green-600',
    bg: 'bg-green-100',
    icon: 'text-green-600'
  },
  purple: {
    text: 'text-purple-600',
    bg: 'bg-purple-100',
    icon: 'text-purple-600'
  },
  orange: {
    text: 'text-orange-600',
    bg: 'bg-orange-100',
    icon: 'text-orange-600'
  }
}

const colorClass = computed(() => colorMap[props.color]?.text || 'text-gray-600')
const iconBgClass = computed(() => colorMap[props.color]?.bg || 'bg-gray-100')
const iconClass = computed(() => colorMap[props.color]?.icon || 'text-gray-600')
</script>
