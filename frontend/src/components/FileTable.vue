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

function splitName(name: string): { base: string; ext: string } {
  const index = name.lastIndexOf('.')
  if (index <= 0) return { base: name, ext: '' }
  return { base: name.slice(0, index), ext: name.slice(index) }
}

function episodeLabel(file: MediaFile): string {
  if (!file.parsed || file.parsed.episode === null) return '—'
  const { season, episode } = file.parsed
  const episodeText = `E${String(episode).padStart(2, '0')}`
  return season === null
    ? episodeText
    : `S${String(season).padStart(2, '0')}${episodeText}`
}

function dotClass(file: MediaFile): string {
  if (!file.parsed) return ''
  if (file.status === 'matched' || file.status === 'renamed') return 'ok'
  if (file.confidence >= 85) return 'ok'
  if (file.confidence >= 60) return 'warn'
  return 'bad'
}

function episodeTagClass(file: MediaFile): string {
  if (!file.parsed) return 'tag-bad'
  if (file.confidence >= 85) return 'tag-ok'
  if (file.confidence >= 60) return 'tag-warn'
  return 'tag-bad'
}
</script>

<template>
  <div class="overflow-x-auto">
    <table class="min-w-[720px]">
      <thead>
        <tr>
          <th v-if="selectable" class="cb pl-4">
            <input
              type="checkbox"
              :checked="allChecked"
              :indeterminate.prop="partial"
              aria-label="全选全部文件"
              @change="toggleAll"
            />
          </th>
          <th>文件名 / FILENAME</th>
          <th>大小</th>
          <th class="th-date">修改时间</th>
          <th v-if="showSource">来源</th>
          <th />
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="file in files"
          :key="file.id"
          :class="{ sel: selectedSet.has(file.id) }"
          :aria-selected="selectedSet.has(file.id)"
          @click="emit('open', file)"
        >
          <td v-if="selectable" class="cb pl-4" @click.stop>
            <input
              type="checkbox"
              :checked="selectedSet.has(file.id)"
              :aria-label="`选择 ${file.original_name}`"
              @change="toggle(file.id)"
            />
          </td>
          <td class="max-w-0">
            <div class="file-cell">
              <span class="dot" :class="dotClass(file)" />
              <span class="fn" :title="file.original_name">
                {{ splitName(file.original_name).base }}<span class="ext">{{ splitName(file.original_name).ext }}</span>
              </span>
            </div>
            <div v-if="showParsed && file.parsed" class="file-sub">
              <span class="tag" :class="episodeTagClass(file)">{{ episodeLabel(file) }}</span>
              <span v-if="file.parsed.title">{{ file.parsed.title }}</span>
              <template v-if="file.parsed.resolution">
                <span class="sep">/</span><span>{{ file.parsed.resolution }}</span>
              </template>
              <template v-if="file.parsed.codec">
                <span class="sep">/</span><span>{{ file.parsed.codec }}</span>
              </template>
            </div>
          </td>
          <td class="cell-size">{{ formatSize(file.size) }}</td>
          <td class="cell-date th-date">{{ formatDate(file.modified_at) }}</td>
          <td v-if="showSource">
            <span class="tag" :class="file.source_type === 'openlist' ? 'tag-info' : 'tag-amber'">
              {{ file.source_type === 'openlist' ? 'OPENLIST' : 'LOCAL' }}
            </span>
          </td>
          <td class="row-actions">
            <span class="tag tag-mute">{{ file.is_video ? 'VID' : 'OTH' }}</span>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
