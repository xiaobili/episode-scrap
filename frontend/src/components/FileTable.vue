<script setup lang="ts">
import { computed, toRef } from 'vue'

import GroupPanel from '@/components/GroupPanel.vue'
import type { GroupBadge } from '@/components/ui-types'
import { useGroupExpansion } from '@/composables/useGroupExpansion'
import type { FolderGroup, SeasonFolderGroup } from '@/composables/useFolderGroups'
import type { MediaFile } from '@/types'

const props = withDefaults(
  defineProps<{
    groups: FolderGroup<MediaFile>[]
    allFiles?: MediaFile[]
    selected: number[]
    selectable?: boolean
    showSource?: boolean
    showParsed?: boolean
    groupStart?: number
  }>(),
  { selectable: true, showSource: false, showParsed: false, groupStart: 0 },
)
const emit = defineEmits<{
  'update:selected': [ids: number[]]
  open: [file: MediaFile]
}>()

const { isShowOpen, isSeasonOpen, toggleShow, toggleSeason } = useGroupExpansion(
  toRef(props, 'groups'),
)

const selectedSet = computed(() => new Set(props.selected))
const selectableIds = computed(() =>
  (props.allFiles ?? props.groups.flatMap((group) => group.items)).map((file) => file.id),
)
const allChecked = computed(
  () =>
    selectableIds.value.length > 0 &&
    selectableIds.value.every((id) => selectedSet.value.has(id)),
)
const partial = computed(
  () =>
    !allChecked.value && selectableIds.value.some((id) => selectedSet.value.has(id)),
)

const columnCount = computed(
  () => 4 + (props.selectable ? 1 : 0) + (props.showSource ? 1 : 0),
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

function allSelected(items: MediaFile[]): boolean {
  return items.length > 0 && items.every((file) => selectedSet.value.has(file.id))
}

function someSelected(items: MediaFile[]): boolean {
  return !allSelected(items) && items.some((file) => selectedSet.value.has(file.id))
}

function toggleItems(items: MediaFile[]) {
  const ids = new Set(items.map((file) => file.id))
  if (allSelected(items)) {
    emit('update:selected', props.selected.filter((id) => !ids.has(id)))
  } else {
    emit('update:selected', Array.from(new Set([...props.selected, ...ids])))
  }
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

function groupIndexLabel(index: number): string {
  return String(props.groupStart + index + 1).padStart(2, '0')
}

function groupMeta(items: MediaFile[], size: number | null): string[] {
  const video = items.filter((file) => file.is_video).length
  const other = items.length - video
  const parts = [`${items.length} 文件`]
  if (video) parts.push(`${video} 视频`)
  if (other) parts.push(`${other} 其他`)
  if (size !== null && size > 0) parts.push(formatSize(size))
  return parts
}

function folderMeta(group: FolderGroup<MediaFile>): string[] {
  const parts = groupMeta(group.items, group.size)
  if (group.seasonCount > 0) parts.push(`${group.seasonCount} 季`)
  return parts
}

function seasonMeta(season: SeasonFolderGroup<MediaFile>): string[] {
  return groupMeta(season.items, season.size)
}

function groupBadges(items: MediaFile[]): GroupBadge[] {
  const unparsed = items.filter((file) => !file.parsed).length
  const matched = items.filter(
    (file) => file.status === 'matched' || file.status === 'renamed',
  ).length
  const badges: GroupBadge[] = []
  if (unparsed) badges.push({ label: `${unparsed} 未解析`, tone: 'warn' })
  if (matched) badges.push({ label: `${matched} 已匹配`, tone: 'ok' })
  return badges
}

function seasonLabel(season: SeasonFolderGroup<MediaFile>): string {
  return season.direct ? '本目录' : season.name
}
</script>

<template>
  <div class="group-scroll overflow-x-auto">
    <table class="group-table min-w-[720px]">
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

      <tbody v-for="(group, groupIndex) in groups" :key="group.key" class="group-body">
        <tr class="group-row">
          <td :colspan="columnCount" class="group-cell">
            <GroupPanel
              level="folder"
              :index="groupIndexLabel(groupIndex)"
              :title="group.title"
              :path="group.path"
              :expanded="isShowOpen(group.key)"
              :selectable="selectable"
              :checked="allSelected(group.items)"
              :indeterminate="someSelected(group.items)"
              :check-label="`选择 ${group.title} 的全部文件`"
              :meta="folderMeta(group)"
              :badges="groupBadges(group.items)"
              @toggle="toggleShow(group.key)"
              @check="toggleItems(group.items)"
            />
          </td>
        </tr>

        <template v-if="isShowOpen(group.key)">
          <template v-for="season in group.seasons" :key="season.key">
            <tr v-if="group.hasSeasons" class="group-row">
              <td :colspan="columnCount" class="group-cell">
                <GroupPanel
                  level="season"
                  :title="seasonLabel(season)"
                  :path="season.path"
                  :expanded="isSeasonOpen(season.key)"
                  :selectable="selectable"
                  :checked="allSelected(season.items)"
                  :indeterminate="someSelected(season.items)"
                  :check-label="`选择 ${group.title} ${seasonLabel(season)} 的全部文件`"
                  :meta="seasonMeta(season)"
                  :badges="groupBadges(season.items)"
                  @toggle="toggleSeason(season.key)"
                  @check="toggleItems(season.items)"
                />
              </td>
            </tr>

            <template v-if="!group.hasSeasons || isSeasonOpen(season.key)">
              <tr
                v-for="file in season.items"
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
                  <span
                    class="tag"
                    :class="file.source_type === 'openlist' ? 'tag-info' : 'tag-amber'"
                  >
                    {{ file.source_type === 'openlist' ? 'OPENLIST' : 'LOCAL' }}
                  </span>
                </td>
                <td class="row-actions">
                  <span class="tag tag-mute">{{ file.is_video ? 'VID' : 'OTH' }}</span>
                </td>
              </tr>
            </template>
          </template>
        </template>
      </tbody>
    </table>
  </div>
</template>
