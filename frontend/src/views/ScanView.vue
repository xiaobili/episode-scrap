<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import AppIcon from '@/components/AppIcon.vue'
import BatchBar from '@/components/BatchBar.vue'
import DataSourceSwitch from '@/components/DataSourceSwitch.vue'
import EmptyState from '@/components/EmptyState.vue'
import ErrorBanner from '@/components/ErrorBanner.vue'
import FileTable from '@/components/FileTable.vue'
import PageHeader from '@/components/PageHeader.vue'
import Pager from '@/components/Pager.vue'
import PathPicker from '@/components/PathPicker.vue'
import SelectMenu from '@/components/SelectMenu.vue'
import StatStrip from '@/components/StatStrip.vue'
import ToggleSwitch from '@/components/ToggleSwitch.vue'
import type { SlateRow, StatItem } from '@/components/ui-types'
import { usePagination } from '@/composables/usePagination'
import { useToast } from '@/composables/useToast'
import { useWorkflowStore } from '@/stores/workflow'
import type { MediaFile, ScanResponse } from '@/types'

const store = useWorkflowStore()
const router = useRouter()
const toast = useToast()

const keyword = ref('')
const onlyVideo = ref(true)
const error = ref('')
const lastScan = ref<ScanResponse | null>(null)

const openlistInstances = computed(() =>
  store.datasources.filter((source) => source.type === 'openlist' && source.id !== null),
)

const visibleFiles = computed(() => {
  const query = keyword.value.trim().toLowerCase()
  return store.files.filter((file) => {
    if (onlyVideo.value && !file.is_video) return false
    return !query || file.original_name.toLowerCase().includes(query)
  })
})

const stats = computed(() => ({
  total: store.files.length,
  video: store.videoFiles.length,
  other: store.files.length - store.videoFiles.length,
}))

const slate = computed<SlateRow[]>(() => [
  { label: 'SOURCE', value: store.sourceType === 'openlist' ? 'OPENLIST' : 'LOCAL' },
  { label: 'ROOT', value: store.scanPath || '—' },
  { label: 'TAKE', value: `${store.files.length} ITEMS` },
  {
    label: 'STATUS',
    value: store.scanning ? 'SCANNING' : store.files.length ? 'READY' : 'IDLE',
    tone: store.scanning ? 'amber' : store.files.length ? 'green' : undefined,
  },
])

const statItems = computed<StatItem[]>(() => [
  { label: 'TOTAL ITEMS', value: stats.value.total },
  { label: 'VIDEO FILES', value: stats.value.video },
  { label: 'OTHER', value: stats.value.other },
  {
    label: 'ELAPSED',
    value: lastScan.value ? (lastScan.value.elapsed_ms / 1000).toFixed(2) : '—',
    unit: lastScan.value ? 's' : undefined,
    tone: 'amber',
  },
])

const scanHint = computed(
  () =>
    `// ${store.settings?.allowed_paths?.length ?? 0} 个白名单目录 · ${
      store.recursive ? '递归扫描' : '仅当前层'
    }`,
)

function chipLabel(file: MediaFile): string {
  const parsed = file.parsed
  if (!parsed || parsed.episode === null) return file.original_name
  return `S${String(parsed.season ?? 1).padStart(2, '0')}E${String(parsed.episode).padStart(2, '0')}`
}

const { page, pageSize, total, pageCount, pageItems, rangeStart, rangeEnd } =
  usePagination(visibleFiles)

watch([keyword, onlyVideo], () => {
  page.value = 1
})

function messageOf(err: unknown) {
  return err instanceof Error ? err.message : '请求失败'
}

async function runScan() {
  error.value = ''
  if (!store.scanPath.trim()) {
    error.value = '请填写要扫描的目录路径'
    return
  }
  if (store.sourceType === 'openlist' && !store.openlistId) {
    error.value = '请选择 OpenList 实例'
    return
  }
  try {
    lastScan.value = await store.scan()
    onlyVideo.value = true
    toast.success(
      `扫描完成：${lastScan.value.video_count} 个视频 / 共 ${lastScan.value.total} 项`,
    )
  } catch (err) {
    error.value = messageOf(err)
  }
}

function openFile(file: MediaFile) {
  if (!file.is_video) return
  store.setSelected([file.id])
  router.push('/parse')
}

watch(
  () => store.sourceType,
  () => {
    store.clearSelection()
    lastScan.value = null
    store.resetScanPath()
  },
)

watch(
  () => store.openlistId,
  (newId, oldId) => {
    if (newId !== oldId && store.sourceType === 'openlist') {
      store.resetScanPath()
    }
  },
)

function onKeydown(event: KeyboardEvent) {
  if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') {
    event.preventDefault()
    void runScan()
  }
}
onMounted(() => document.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => document.removeEventListener('keydown', onKeydown))
</script>

<template>
  <div>
    <PageHeader
      ghost="01"
      kicker="STEP 01 · INGEST"
      title="扫描"
      title-en="SCAN"
      description="选择剧集所在位置，扫描后自动解析文件名。支持本地白名单目录与 OpenList 云盘。"
      :slate="slate"
    />

    <section class="panel">
      <div class="scan-controls">
        <div class="controls-top">
          <DataSourceSwitch v-model="store.sourceType" :sources="store.datasources" />
          <span class="hint">{{ scanHint }}</span>
        </div>

        <div class="controls-main scan-controls-main">
          <PathPicker
            v-model="store.scanPath"
            :source-type="store.sourceType"
            :openlist-id="store.openlistId"
            :allowed-roots="store.settings?.allowed_paths ?? []"
          />

          <div class="field">
            <label>递归 <span>RECURSIVE</span></label>
            <ToggleSwitch v-model="store.recursive" label="含子目录" />
          </div>

          <div v-if="store.sourceType === 'openlist'" class="field">
            <label>OpenList 实例 <span>INSTANCE</span></label>
            <div v-if="openlistInstances.length" class="flex gap-2">
              <SelectMenu
                v-model="store.openlistId"
                class="min-w-[160px]"
                :options="openlistInstances.map((i) => ({ value: i.id!, label: i.name }))"
              />
              <button class="btn btn-sm flex-none" @click="router.push('/settings')">管理</button>
            </div>
            <div v-else class="warn-note">
              <AppIcon name="alert" :size="14" />
              <span>尚未配置实例，<button class="text-amber hover:underline" @click="router.push('/settings')">去配置</button></span>
            </div>
          </div>
          <div v-else />

          <button class="btn btn-amber scan-btn" :disabled="store.scanning" @click="runScan">
            <AppIcon name="scan" :size="14" :spin="store.scanning" />
            {{ store.scanning ? '扫描中…' : '开始扫描' }}
          </button>
        </div>
      </div>
      <div class="scan-line" :class="{ on: store.scanning }"><i /></div>
    </section>

    <ErrorBanner v-if="error" class="mt-3" title="无法扫描" :message="error" />

    <StatStrip class="mt-3.5" :items="statItems" />

    <section class="panel">
      <div class="table-toolbar">
        <div class="toolbar-title">
          <span>FILE INDEX</span>
          <b>{{ rangeStart }}–{{ rangeEnd }} / {{ total }}</b>
          <span v-if="!store.scanning && visibleFiles.length" class="tag tag-ok">SCAN OK</span>
        </div>
        <div class="toolbar-right">
          <ToggleSwitch v-model="onlyVideo" label="仅看视频" size="sm" />
          <div class="search-mini">
            <AppIcon name="search" :size="13" />
            <input v-model="keyword" placeholder="筛选文件名…" spellcheck="false" aria-label="筛选文件名" />
          </div>
        </div>
      </div>

      <div v-if="store.scanning" class="divide-y divide-line/60">
        <div v-for="index in 6" :key="index" class="flex h-11 items-center gap-4 px-4">
          <span class="h-3.5 w-3.5 animate-pulse rounded bg-[var(--surface-2)]" />
          <span class="h-3 flex-1 animate-pulse rounded bg-[var(--surface-2)]" />
          <span class="h-3 w-16 animate-pulse rounded bg-[var(--surface-2)]" />
          <span class="h-3 w-24 animate-pulse rounded bg-[var(--surface-2)]" />
        </div>
      </div>

      <FileTable
        v-else-if="visibleFiles.length"
        :files="pageItems"
        :all-files="visibleFiles"
        :selected="store.selectedIds"
        show-parsed
        show-source
        @update:selected="store.setSelected"
        @open="openFile"
      />

      <EmptyState
        v-else-if="store.files.length === 0"
        icon="scan"
        title="还没有扫描任何文件"
        description="在上方填写目录路径后开始扫描，支持本地目录与 OpenList 云盘。"
      >
        <button class="btn btn-amber" :disabled="store.scanning" @click="runScan">
          <AppIcon name="scan" :size="14" />
          开始扫描
        </button>
      </EmptyState>

      <EmptyState
        v-else
        icon="filter"
        title="没有匹配的文件"
        description="当前筛选条件下没有结果，试试关闭「仅看视频」或清空关键词。"
      />

      <Pager
        v-if="!store.scanning && visibleFiles.length"
        v-model:page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-count="pageCount"
      />
    </section>

    <BatchBar
      :count="store.selectedFiles.length"
      :total="store.files.length"
      :chips="store.selectedFiles.slice(0, 4).map(chipLabel)"
      next-label="下一步：解析"
      @clear="store.clearSelection"
      @next="router.push('/parse')"
    >
      <span class="text-[11.5px] text-faint">
        已选视频 {{ store.selectedFiles.filter((file) => file.is_video).length }} 个
      </span>
    </BatchBar>
  </div>
</template>
