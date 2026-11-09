<script setup lang="ts">
import { computed } from 'vue'

import AppIcon from '@/components/AppIcon.vue'
import type { Episode, MediaFile } from '@/types'

const props = defineProps<{
  files: MediaFile[]
  episodes: Episode[]
  season: number | null
}>()

interface Row {
  fileId: number
  name: string
  local: string
  target: string | null
  ok: boolean
}

const rows = computed<Row[]>(() =>
  props.files.map((file) => {
    const parsed = file.parsed
    const localEpisode = parsed?.episode ?? null
    const episode =
      localEpisode === null
        ? undefined
        : props.episodes.find((item) => item.episode === localEpisode)
    const local =
      parsed && localEpisode !== null
        ? `S${String(parsed.season ?? props.season ?? 1).padStart(2, '0')}E${String(localEpisode).padStart(2, '0')}`
        : '未知集'
    return {
      fileId: file.id,
      name: file.original_name,
      local,
      target: episode
        ? `S${String(props.season ?? 1).padStart(2, '0')}E${String(episode.episode).padStart(2, '0')}${episode.title ? ` · ${episode.title}` : ''}`
        : null,
      ok: Boolean(episode),
    }
  }),
)

const missing = computed(() => rows.value.filter((row) => !row.ok).length)
</script>

<template>
  <div class="flex h-full flex-col">
    <div class="flex items-center justify-between border-b border-line px-3 py-2">
      <span class="text-xs font-medium text-muted">季集映射</span>
      <span class="font-mono text-[11px] text-faint">
        {{ rows.length - missing }}/{{ rows.length }}
      </span>
    </div>

    <div v-if="rows.length === 0" class="px-3 py-8 text-center text-xs text-faint">
      请选择需要匹配的文件
    </div>

    <div v-else class="min-h-0 flex-1 overflow-y-auto">
      <div
        v-for="row in rows"
        :key="row.fileId"
        class="flex items-start gap-2 border-b border-line/60 px-3 py-2 text-[12px] last:border-0"
        :class="row.ok ? '' : 'bg-[rgba(245,184,73,.07)]'"
        :title="row.name"
      >
        <AppIcon
          :name="row.ok ? 'check-circle' : 'alert'"
          :size="13"
          class="mt-0.5 flex-none"
          :class="row.ok ? 'text-success' : 'text-warning'"
        />
        <span class="min-w-0 flex-1">
          <span class="block font-mono text-[11px] text-faint">{{ row.local }}</span>
          <span v-if="row.ok" class="block truncate text-[12px] text-ink">→ {{ row.target }}</span>
          <span v-else class="block text-[11.5px] text-warning">未找到对应集</span>
        </span>
      </div>
    </div>

    <p v-if="missing > 0" class="border-t border-line px-3 py-2 text-[11.5px] text-warning">
      {{ missing }} 项无法按集号对齐，将不会被匹配
    </p>
  </div>
</template>
