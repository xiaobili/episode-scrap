<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import AppIcon from '@/components/AppIcon.vue'
import BatchBar from '@/components/BatchBar.vue'
import DataSourceSwitch from '@/components/DataSourceSwitch.vue'
import EmptyState from '@/components/EmptyState.vue'
import ErrorBanner from '@/components/ErrorBanner.vue'
import FileTable from '@/components/FileTable.vue'
import Pager from '@/components/Pager.vue'
import PathPicker from '@/components/PathPicker.vue'
import SelectMenu from '@/components/SelectMenu.vue'
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

const { page, pageSize, total, pageCount, pageItems } = usePagination(visibleFiles)

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
    <header class="mb-5">
      <h1 class="text-2xl font-semibold leading-8 tracking-tight text-ink">扫描</h1>
      <p class="mt-1 text-[13px] text-muted">选择剧集所在位置，扫描后可解析文件名</p>
    </header>

    <section class="panel p-4 md:p-5">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <DataSourceSwitch v-model="store.sourceType" :sources="store.datasources" />
        <span class="text-[11.5px] text-faint">
          {{ store.sourceType === 'openlist' ? '通过 OpenList 云盘读取' : '读取本机白名单目录' }}
        </span>
      </div>

      <div class="mt-4">
        <PathPicker
          v-model="store.scanPath"
          v-model:recursive="store.recursive"
          :source-type="store.sourceType"
          :openlist-id="store.openlistId"
          :allowed-roots="store.settings?.allowed_paths ?? []"
        />
      </div>

      <div class="mt-4 flex flex-wrap items-end justify-between gap-3">
        <div v-if="store.sourceType === 'openlist'" class="w-full max-w-xs">
          <label class="label">OpenList 实例</label>
          <div v-if="openlistInstances.length" class="flex gap-2">
            <SelectMenu
              v-model="store.openlistId"
              class="flex-1"
              :options="openlistInstances.map((i) => ({ value: i.id!, label: i.name }))"
            />
            <button class="btn flex-none" @click="router.push('/settings')">管理</button>
          </div>
          <div
            v-else
            class="flex h-8 items-center gap-2 rounded-md border border-dashed border-line-strong px-2.5 text-xs text-muted"
          >
            尚未配置实例
            <button class="text-accent hover:underline" @click="router.push('/settings')">
              去配置
            </button>
          </div>
        </div>
        <span v-else class="text-[11.5px] text-faint">
          支持扫描白名单目录下的视频与字幕文件
        </span>

        <button class="btn btn-primary ml-auto" :disabled="store.scanning" @click="runScan">
          <AppIcon name="scan" :size="14" :spin="store.scanning" />
          {{ store.scanning ? '扫描中…' : '开始扫描' }}
        </button>
      </div>

      <ErrorBanner v-if="error" class="mt-3" title="无法扫描" :message="error" />
    </section>

    <section class="mt-5">
      <div class="mb-2.5 flex flex-wrap items-center gap-x-4 gap-y-2">
        <div class="flex items-baseline gap-3 text-[12.5px] text-muted">
          <span>共 <b class="font-mono text-ink">{{ stats.total }}</b> 项</span>
          <span>视频 <b class="font-mono text-ink">{{ stats.video }}</b></span>
          <span>其他 <b class="font-mono text-ink">{{ stats.other }}</b></span>
          <span v-if="lastScan" class="text-faint">
            {{ (lastScan.elapsed_ms / 1000).toFixed(2) }}s
          </span>
        </div>

        <div class="ml-auto flex items-center gap-3">
          <label class="flex cursor-pointer select-none items-center gap-1.5 text-xs text-muted">
            <input v-model="onlyVideo" type="checkbox" class="h-3.5 w-3.5 accent-accent" />
            仅看视频
          </label>
          <div class="relative">
            <AppIcon
              name="search"
              :size="13"
              class="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-faint"
            />
            <input
              v-model="keyword"
              class="input h-8 w-52 pl-7 text-xs"
              placeholder="筛选文件名"
              spellcheck="false"
            />
          </div>
        </div>
      </div>

      <div class="panel overflow-hidden">
        <div v-if="store.scanning" class="divide-y divide-line/60">
          <div v-for="index in 6" :key="index" class="flex h-11 items-center gap-4 px-3">
            <span class="h-3.5 w-3.5 animate-pulse rounded bg-[var(--bg-elevated)]" />
            <span class="h-3 flex-1 animate-pulse rounded bg-[var(--bg-elevated)]" />
            <span class="h-3 w-16 animate-pulse rounded bg-[var(--bg-elevated)]" />
            <span class="h-3 w-24 animate-pulse rounded bg-[var(--bg-elevated)]" />
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
          <button class="btn btn-primary" :disabled="store.scanning" @click="runScan">
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
      </div>
    </section>

    <BatchBar
      :count="store.selectedFiles.length"
      next-label="下一步：解析"
      @clear="store.clearSelection"
      @next="router.push('/parse')"
    >
      <span class="text-[11.5px] text-faint">已选视频 {{ store.selectedFiles.filter((file) => file.is_video).length }} 个</span>
    </BatchBar>
  </div>
</template>
