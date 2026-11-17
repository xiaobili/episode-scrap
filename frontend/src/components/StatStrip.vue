<script setup lang="ts">
import type { StatItem } from '@/components/ui-types'

defineProps<{ items: StatItem[] }>()
</script>

<template>
  <div class="stats">
    <div v-for="item in items" :key="item.label" class="stat">
      <div class="k">{{ item.label }}</div>
      <b :class="item.tone">
        {{ item.value }}
        <em v-if="item.unit">{{ item.unit }}</em>
      </b>
      <span class="spark" aria-hidden="true">
        <i /><i /><i /><i /><i />
      </span>
    </div>
  </div>
</template>
