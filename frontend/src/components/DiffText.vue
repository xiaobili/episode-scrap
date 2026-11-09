<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ before: string; after: string }>()

interface Segment {
  text: string
  changed: boolean
}

function diff(before: string, after: string): Segment[] {
  if (!before) return after ? [{ text: after, changed: true }] : []
  if (!after) return []
  if (before.length * after.length > 200000) return [{ text: after, changed: true }]

  const rows = before.length + 1
  const cols = after.length + 1
  const table: number[][] = Array.from({ length: rows }, () => new Array<number>(cols).fill(0))
  for (let i = before.length - 1; i >= 0; i -= 1) {
    for (let j = after.length - 1; j >= 0; j -= 1) {
      table[i][j] =
        before[i] === after[j] ? table[i + 1][j + 1] + 1 : Math.max(table[i + 1][j], table[i][j + 1])
    }
  }

  const segments: Segment[] = []
  let current: Segment | null = null
  const push = (text: string, changed: boolean) => {
    if (current && current.changed === changed) current.text += text
    else {
      current = { text, changed }
      segments.push(current)
    }
  }

  let i = 0
  let j = 0
  while (i < before.length && j < after.length) {
    if (before[i] === after[j]) {
      push(after[j], false)
      i += 1
      j += 1
    } else if (table[i + 1][j] >= table[i][j + 1]) {
      i += 1
    } else {
      push(after[j], true)
      j += 1
    }
  }
  while (j < after.length) {
    push(after[j], true)
    j += 1
  }
  return segments
}

const segments = computed(() => diff(props.before, props.after))
</script>

<template>
  <span class="block truncate font-mono text-xs" :title="after">
    <span
      v-for="(segment, index) in segments"
      :key="index"
      :class="
        segment.changed
          ? 'rounded-sm bg-[rgba(61,214,140,.16)] px-px text-success'
          : 'text-muted'
      "
      >{{ segment.text }}</span
    >
  </span>
</template>
