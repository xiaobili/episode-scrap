<script setup lang="ts">
import { computed } from 'vue'

import AppIcon from '@/components/AppIcon.vue'
import type { Episode, MediaFile } from '@/types'

const props = defineProps<{
  files: MediaFile[]
  episodesBySeason: Record<number, Episode[]>
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
    const seasonNo = parsed?.season ?? props.season ?? 1
    const episodes = props.episodesBySeason[seasonNo] ?? []
    const episode =
      localEpisode === null
        ? undefined
        : episodes.find((item) => item.episode === localEpisode)
    const local =
      parsed && localEpisode !== null
        ? `S${String(seasonNo).padStart(2, '0')}E${String(localEpisode).padStart(2, '0')}`
        : '未知集'
    return {
      fileId: file.id,
      name: file.original_name,
      local,
      target: episode
        ? `E${String(episode.episode).padStart(2, '0')}${episode.title ? ` ${episode.title}` : ''}`
        : null,
      ok: Boolean(episode),
    }
  }),
)

const missing = computed(() => rows.value.filter((row) => !row.ok).length)
</script>

<template>
  <div class="map-list">
    <div v-if="rows.length === 0" class="px-3 py-8 text-center text-xs text-faint">
      请选择需要匹配的文件
    </div>

    <template v-else>
      <div
        v-for="row in rows"
        :key="row.fileId"
        class="map-row"
        :class="{ warn: !row.ok }"
        :title="row.name"
      >
        <span class="from">{{ row.local }}</span>
        <span class="arw">→</span>
        <span class="to">
          <template v-if="row.ok">{{ row.target }}</template>
          <template v-else>
            <AppIcon name="alert" :size="12" />
            未找到对应剧集
          </template>
        </span>
      </div>
    </template>

    <p v-if="missing > 0" class="px-3 py-2 text-[10.5px] text-warning">
      {{ missing }} 项无法按集号对齐，将不会被匹配
    </p>
  </div>
</template>
