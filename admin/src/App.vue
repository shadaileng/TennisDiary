<template>
  <router-view />
  <Toast />
  <Loading />
</template>

<script setup lang="ts">
import Toast from '@/components/common/Toast.vue'
import Loading from '@/components/common/Loading.vue'
</script>
