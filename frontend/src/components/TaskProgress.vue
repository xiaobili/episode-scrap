<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  total: number
  done: number
  failed: number
  status?: string
}>()

const percent = computed(() => {
  if (!props.total) return props.status === 'completed' ? 100 : 0
  return Math.min(100, Math.round(((props.done + props.failed) / props.total) * 100))
})

const tone = computed(() => {
  if (props.failed > 0) return 'bg-danger'
  if (props.status === 'completed') return 'bg-success'
  return 'bg-accent'
})
</script>

<template>
  <div class="min-w-[140px]">
    <div class="mb-1.5 flex items-baseline justify-between gap-2 text-[11.5px]">
      <span class="font-mono text-muted">{{ done + failed }}/{{ total }}</span>
      <span class="font-mono" :class="failed > 0 ? 'text-danger' : 'text-faint'">
        {{ percent }}%
      </span>
    </div>
    <div
      class="h-1.5 w-full overflow-hidden rounded-full bg-[var(--bg-elevated)]"
      role="progressbar"
      :aria-valuenow="percent"
      aria-valuemin="0"
      aria-valuemax="100"
    >
      <div
        class="h-full rounded-full transition-[width] duration-300"
        :class="tone"
        :style="{ width: `${percent}%` }"
      />
    </div>
  </div>
</template>
