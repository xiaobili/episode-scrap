<script setup lang="ts">
import AppIcon from '@/components/AppIcon.vue'

withDefaults(
  defineProps<{
    icon?: string
    title: string
    description?: string
  }>(),
  { icon: 'film' },
)
</script>

<template>
  <div class="flex flex-col items-center justify-center px-6 py-16 text-center">
    <span
      class="mb-4 grid h-14 w-14 place-items-center rounded-xl border border-line bg-[var(--bg-elevated)] text-muted"
    >
      <AppIcon :name="icon" :size="26" :stroke="1.5" />
    </span>
    <h3 class="text-[15px] font-semibold text-ink">{{ title }}</h3>
    <p v-if="description" class="mt-1.5 max-w-sm text-[13px] leading-6 text-muted">
      {{ description }}
    </p>
    <div v-if="$slots.default" class="mt-5 flex flex-wrap items-center justify-center gap-2">
      <slot />
    </div>
  </div>
</template>
