<template>
  <nav class="flex" aria-label="Breadcrumb">
    <ol class="flex items-center space-x-2">
      <li v-for="(item, index) in breadcrumbs" :key="index" class="flex items-center">
        <router-link
          v-if="item.path"
          :to="item.path"
          class="text-sm text-gray-500 hover:text-olive-600"
        >
          {{ item.title }}
        </router-link>
        <span v-else class="text-sm text-gray-700 font-medium">
          {{ item.title }}
        </span>
        <ChevronRightIcon
          v-if="index < breadcrumbs.length - 1"
          class="w-4 h-4 mx-2 text-gray-400"
        />
      </li>
    </ol>
  </nav>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { ChevronRightIcon } from '@heroicons/vue/24/outline'

const route = useRoute()

const breadcrumbs = computed(() => {
  const matched = route.matched.filter(item => item.meta?.title)
  return matched.map(item => ({
    title: item.meta.title as string,
    path: item.redirect ? '' : item.path
  }))
})
</script>
