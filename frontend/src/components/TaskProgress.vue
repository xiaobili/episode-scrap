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

const success = computed(() => props.status === 'completed' && props.failed === 0)
const danger = computed(() => props.failed > 0)
</script>

<template>
  <div class="min-w-[140px]">
    <div class="progress-top">
      <span>{{ done + failed }}/{{ total }}</span>
      <b>{{ percent }}%</b>
    </div>
    <div
      class="bar"
      :class="{ green: success, danger }"
      role="progressbar"
      :aria-valuenow="percent"
      aria-valuemin="0"
      aria-valuemax="100"
    >
      <i :style="{ width: `${percent}%` }" />
    </div>
  </div>
</template>
