<script setup lang="ts">
import { computed } from 'vue'

import AppIcon from '@/components/AppIcon.vue'

const props = withDefaults(
  defineProps<{
    page: number
    pageCount: number
    total: number
    pageSize: number
    pageSizes?: number[]
  }>(),
  { pageSizes: () => [10, 20, 50, 100] },
)

const emit = defineEmits<{
  'update:page': [page: number]
  'update:pageSize': [size: number]
}>()

const pages = computed<(number | null)[]>(() => {
  const count = props.pageCount
  if (count <= 7) return Array.from({ length: count }, (_, index) => index + 1)

  const values = new Set<number>([1, count, props.page - 1, props.page, props.page + 1])
  const ordered = [...values].filter((value) => value >= 1 && value <= count).sort((a, b) => a - b)
  const result: (number | null)[] = []
  let previous = 0
  for (const value of ordered) {
    if (previous && value - previous > 1) result.push(null)
    result.push(value)
    previous = value
  }
  return result
})

function go(page: number | null) {
  if (page === null) return
  const next = Math.min(Math.max(page, 1), props.pageCount)
  if (next !== props.page) emit('update:page', next)
}

function changePageSize(event: Event) {
  emit('update:pageSize', Number((event.target as HTMLSelectElement).value))
}
</script>

<template>
  <div
    class="flex flex-wrap items-center gap-x-3 gap-y-2 border-t border-line px-3 py-2 text-[11.5px] text-muted"
  >
    <span>
      共 <b class="font-mono text-ink">{{ total }}</b> 条
    </span>
    <label class="flex items-center gap-1.5">
      每页
      <select class="select h-7 !w-auto text-xs" :value="pageSize" @change="changePageSize">
        <option v-for="size in pageSizes" :key="size" :value="size">{{ size }}</option>
      </select>
    </label>

    <div class="ml-auto flex items-center gap-1">
      <button class="btn btn-xs" :disabled="page <= 1" @click="go(page - 1)">
        <AppIcon name="chevron-left" :size="12" />
        上一页
      </button>

      <template v-for="(item, index) in pages" :key="index">
        <span v-if="item === null" class="px-1 text-faint">…</span>
        <button
          v-else
          class="grid h-7 min-w-7 place-items-center rounded border px-1.5 font-mono text-[11px] transition"
          :class="
            item === page
              ? 'border-accent bg-[var(--accent-soft)] text-accent'
              : 'border-transparent text-muted hover:border-line-strong hover:text-ink'
          "
          :aria-current="item === page ? 'page' : undefined"
          @click="go(item)"
        >
          {{ item }}
        </button>
      </template>

      <button class="btn btn-xs" :disabled="page >= pageCount" @click="go(page + 1)">
        下一页
        <AppIcon name="chevron-right" :size="12" />
      </button>
    </div>
  </div>
</template>
