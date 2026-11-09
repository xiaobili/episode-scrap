<script setup lang="ts">
import { ref } from 'vue'

import AppIcon from '@/components/AppIcon.vue'
import type { Show } from '@/types'

defineProps<{ show: Show; selected?: boolean }>()
const emit = defineEmits<{ select: [show: Show] }>()

const failed = ref(false)
</script>

<template>
  <button
    class="flex w-full items-start gap-3 rounded-lg border p-2 text-left transition"
    :class="
      selected
        ? 'border-accent bg-[var(--accent-soft)]'
        : 'border-line bg-surface hover:border-line-strong hover:bg-[var(--bg-elevated)]'
    "
    @click="emit('select', show)"
  >
    <span
      class="grid h-[78px] w-[52px] flex-none place-items-center overflow-hidden rounded border border-line bg-base text-faint"
    >
      <img
        v-if="show.poster_url && !failed"
        :src="show.poster_url"
        :alt="show.title"
        class="h-full w-full object-cover"
        loading="lazy"
        @error="failed = true"
      />
      <AppIcon v-else name="film" :size="20" />
    </span>

    <span class="min-w-0 flex-1 py-0.5">
      <span class="block truncate text-[13px] font-medium text-ink">{{ show.title }}</span>
      <span
        v-if="show.original_title && show.original_title !== show.title"
        class="mt-0.5 block truncate text-[11.5px] text-faint"
      >
        {{ show.original_title }}
      </span>
      <span class="mt-1 flex flex-wrap items-center gap-x-2.5 gap-y-1 text-[11.5px] text-muted">
        <span v-if="show.year">{{ show.year }}</span>
        <span v-if="show.rating" class="inline-flex items-center gap-0.5 text-warning">
          <AppIcon name="scrape" :size="11" />
          {{ show.rating.toFixed(1) }}
        </span>
        <span>{{ show.seasons_count }} 季</span>
      </span>
      <span v-if="show.overview" class="mt-1 line-clamp-2 text-[11.5px] leading-4 text-faint">
        {{ show.overview }}
      </span>
    </span>

    <span
      class="mt-0.5 flex-none rounded border px-1.5 py-0.5 text-[10.5px]"
      :class="selected ? 'border-accent text-accent' : 'border-line text-faint'"
    >
      {{ selected ? '已选择' : '选择' }}
    </span>
  </button>
</template>
