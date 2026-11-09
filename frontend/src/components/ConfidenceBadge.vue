<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ value: number }>()

const level = computed(() => {
  if (props.value >= 85) return { label: '高', tone: 'tag-success' }
  if (props.value >= 60) return { label: '待确认', tone: 'tag-warning' }
  return { label: '低', tone: 'tag-danger' }
})
</script>

<template>
  <span class="tag" :class="level.tone">
    {{ level.label }}
    <span class="font-mono text-[10.5px] opacity-80">{{ value }}%</span>
  </span>
</template>
