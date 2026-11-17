<script setup lang="ts">
import AppShell from '@/components/AppShell.vue'
import ToastHost from '@/components/ToastHost.vue'
</script>

<template>
  <div class="ambient" aria-hidden="true" />
  <div class="scanlines" aria-hidden="true" />
  <div class="grain" aria-hidden="true" />
  <AppShell />
  <ToastHost />
</template>
