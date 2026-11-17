<script setup lang="ts">
import type { SlateRow } from '@/components/ui-types'

withDefaults(
  defineProps<{
    ghost: string
    kicker: string
    title: string
    titleEn?: string
    description?: string
    slate?: SlateRow[]
  }>(),
  { titleEn: '', description: '', slate: () => [] },
)
</script>

<template>
  <header class="page-head">
    <span class="ghost-num">{{ ghost }}</span>
    <div class="head-copy">
      <div class="kicker">{{ kicker }}</div>
      <h1>
        {{ title }}
        <span v-if="titleEn" class="h1-en">{{ titleEn }}</span>
      </h1>
      <p v-if="description" class="head-desc">{{ description }}</p>
      <div v-if="$slots.actions" class="head-actions">
        <slot name="actions" />
      </div>
    </div>
    <div v-if="slate.length" class="slate">
      <div class="slate-stripe" />
      <div class="slate-body">
        <div v-for="row in slate" :key="row.label" class="slate-row">
          <span>{{ row.label }}</span>
          <b :class="row.tone">{{ row.value }}</b>
        </div>
      </div>
    </div>
    <slot name="slate" />
  </header>
</template>
