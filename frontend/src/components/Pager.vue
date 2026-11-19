<script setup lang="ts">
import { computed } from 'vue'

import AppIcon from '@/components/AppIcon.vue'
import SelectMenu from '@/components/SelectMenu.vue'

const props = withDefaults(
  defineProps<{
    page: number
    pageCount: number
    total: number
    pageSize: number
    pageSizes?: number[]
    compact?: boolean
    unit?: string
  }>(),
  { pageSizes: () => [10, 20, 50, 100], compact: false, unit: '条' },
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

const sizeOptions = computed(() =>
  props.pageSizes.map((s) => ({ value: s, label: String(s) })),
)

const pageSizeValue = computed({
  get: () => props.pageSize,
  set: (v: string | number | null) => emit('update:pageSize', Number(v)),
})

function go(page: number | null) {
  if (page === null) return
  const next = Math.min(Math.max(page, 1), props.pageCount)
  if (next !== props.page) emit('update:page', next)
}
</script>

<template>
  <div class="table-foot">
    <template v-if="compact">
      <span>{{ page }} / {{ pageCount }}</span>
      <div class="pager ml-auto">
        <button :disabled="page <= 1" aria-label="上一页" @click="go(page - 1)">
          <AppIcon name="chevron-left" :size="12" />
        </button>
        <button :disabled="page >= pageCount" aria-label="下一页" @click="go(page + 1)">
          <AppIcon name="chevron-right" :size="12" />
        </button>
      </div>
    </template>

    <template v-else>
      <span>
        共 <b class="text-ink">{{ total }}</b> {{ unit }} · 第 {{ page }} / {{ pageCount }} 页
      </span>

      <label class="flex items-center gap-1.5">
        每页
        <SelectMenu v-model="pageSizeValue" class="h-7 !w-auto text-xs" :options="sizeOptions" />
        {{ unit }}
      </label>

      <div class="pager ml-auto">
        <button :disabled="page <= 1" aria-label="上一页" @click="go(page - 1)">
          <AppIcon name="chevron-left" :size="12" />
        </button>

        <template v-for="(item, index) in pages" :key="index">
          <span v-if="item === null" class="px-1 text-faint">…</span>
          <button
            v-else
            :class="{ on: item === page }"
            :aria-current="item === page ? 'page' : undefined"
            @click="go(item)"
          >
            {{ item }}
          </button>
        </template>

        <button :disabled="page >= pageCount" aria-label="下一页" @click="go(page + 1)">
          <AppIcon name="chevron-right" :size="12" />
        </button>
      </div>
    </template>
  </div>
</template>
