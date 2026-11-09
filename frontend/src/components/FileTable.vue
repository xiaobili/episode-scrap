<script setup lang="ts">
import { computed } from 'vue'

import StatusTag from '@/components/StatusTag.vue'
import type { MediaFile } from '@/types'

const props = withDefaults(
  defineProps<{
    files: MediaFile[]
    allFiles?: MediaFile[]
    selected: number[]
    selectable?: boolean
    showSource?: boolean
    showParsed?: boolean
  }>(),
  { selectable: true, showSource: false, showParsed: false },
)
const emit = defineEmits<{
  'update:selected': [ids: number[]]
  open: [file: MediaFile]
}>()

const selectedSet = computed(() => new Set(props.selected))
const selectableIds = computed(() => (props.allFiles ?? props.files).map((file) => file.id))
const allChecked = computed(
  () =>
    selectableIds.value.length > 0 &&
    selectableIds.value.every((id) => selectedSet.value.has(id)),
)
const partial = computed(
  () =>
    !allChecked.value && selectableIds.value.some((id) => selectedSet.value.has(id)),
)

function toggleAll() {
  if (allChecked.value) {
    const keep = new Set(selectableIds.value)
    emit('update:selected', props.selected.filter((id) => !keep.has(id)))
  } else {
    emit('update:selected', Array.from(new Set([...props.selected, ...selectableIds.value])))
  }
}

function toggle(id: number) {
  emit(
    'update:selected',
    selectedSet.value.has(id)
      ? props.selected.filter((item) => item !== id)
      : [...props.selected, id],
  )
}

function formatSize(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes <= 0) return '—'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let value = bytes
  let unit = 0
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024
    unit += 1
  }
  return `${value.toFixed(unit === 0 ? 0 : 1)} ${units[unit]}`
}

function formatDate(value: string | null): string {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  const pad = (num: number) => String(num).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

function episodeLabel(file: MediaFile): string {
  if (!file.parsed || file.parsed.episode === null) return '—'
  const { season, episode } = file.parsed
  const episodeText = `E${String(episode).padStart(2, '0')}`
  return season === null
    ? episodeText
    : `S${String(season).padStart(2, '0')}${episodeText}`
}
</script>

<template>
  <div class="overflow-x-auto">
    <table class="w-full min-w-[720px] border-collapse text-[13px]">
      <thead>
        <tr class="border-b border-line text-left text-xs text-faint">
          <th v-if="selectable" class="h-10 w-10 pl-3">
            <input
              type="checkbox"
              class="h-4 w-4 accent-accent"
              :checked="allChecked"
              :indeterminate.prop="partial"
              aria-label="全选全部文件"
              @change="toggleAll"
            />
          </th>
          <th class="h-10 px-3 font-medium">文件名</th>
          <th v-if="showParsed" class="h-10 w-24 px-2 font-medium">季集</th>
          <th class="h-10 w-28 px-2 font-medium">状态</th>
          <th class="h-10 w-24 px-2 text-right font-medium">大小</th>
          <th class="h-10 w-40 px-2 font-medium">修改时间</th>
          <th v-if="showSource" class="h-10 w-24 px-3 font-medium">来源</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="file in files"
          :key="file.id"
          class="h-11 border-b border-line/60 transition-colors last:border-0"
          :class="selectedSet.has(file.id) ? 'bg-[var(--accent-soft)]' : 'hover:bg-[var(--bg-elevated)]'"
          :aria-selected="selectedSet.has(file.id)"
          @click="emit('open', file)"
        >
          <td v-if="selectable" class="pl-3" @click.stop>
            <input
              type="checkbox"
              class="h-4 w-4 accent-accent"
              :checked="selectedSet.has(file.id)"
              :aria-label="`选择 ${file.original_name}`"
              @change="toggle(file.id)"
            />
          </td>
          <td class="max-w-0 px-3">
            <div class="flex items-center gap-2">
              <span
                class="flex-none rounded border border-line px-1 py-px font-mono text-[10px] uppercase text-faint"
              >
                {{ file.is_video ? 'VID' : 'OTH' }}
              </span>
              <span class="truncate font-mono text-xs" :title="file.original_name">
                {{ file.original_name }}
              </span>
            </div>
          </td>
          <td v-if="showParsed" class="px-2 font-mono text-xs text-muted">
            {{ episodeLabel(file) }}
          </td>
          <td class="px-2"><StatusTag :status="file.status" /></td>
          <td class="px-2 text-right font-mono text-xs text-muted">{{ formatSize(file.size) }}</td>
          <td class="px-2 font-mono text-xs text-faint">{{ formatDate(file.modified_at) }}</td>
          <td v-if="showSource" class="px-3">
            <span class="tag" :class="file.source_type === 'openlist' ? 'tag-info' : ''">
              {{ file.source_type === 'openlist' ? 'OpenList' : '本地' }}
            </span>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
