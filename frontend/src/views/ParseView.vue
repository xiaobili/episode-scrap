<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import AppIcon from '@/components/AppIcon.vue'
import ConfidenceBadge from '@/components/ConfidenceBadge.vue'
import EmptyState from '@/components/EmptyState.vue'
import ErrorBanner from '@/components/ErrorBanner.vue'
import { useToast } from '@/composables/useToast'
import { useWorkflowStore } from '@/stores/workflow'
import type { MediaFile } from '@/types'

type FilterKey = 'all' | 'todo' | 'unparsed'

interface Draft {
  title: string
  year: string
  season: string
  episode: string
  episode_end: string
  episode_title: string
  resolution: string
  codec: string
  release_group: string
}

function blankDraft(): Draft {
  return {
    title: '',
    year: '',
    season: '',
    episode: '',
    episode_end: '',
    episode_title: '',
    resolution: '',
    codec: '',
    release_group: '',
  }
}

const store = useWorkflowStore()
const router = useRouter()
const toast = useToast()

const filter = ref<FilterKey>('all')
const activeId = ref<number | null>(null)
const draft = ref<Draft>(blankDraft())
const saving = ref(false)
const reparsing = ref(false)
const batchParsing = ref(false)
const error = ref('')

const files = computed(() => store.videoFiles)

function needsReview(file: MediaFile) {
  return Boolean(file.parsed) && (file.confidence < 85 || !file.parsed?.title)
}

const counts = computed(() => ({
  all: files.value.length,
  todo: files.value.filter(needsReview).length,
  unparsed: files.value.filter((file) => !file.parsed).length,
}))

const filtered = computed(() => {
  if (filter.value === 'todo') return files.value.filter(needsReview)
  if (filter.value === 'unparsed') return files.value.filter((file) => !file.parsed)
  return files.value
})

const active = computed(() => files.value.find((file) => file.id === activeId.value) ?? null)
const activeIndex = computed(() => filtered.value.findIndex((file) => file.id === activeId.value))

const titleInvalid = computed(() => !draft.value.title.trim())
const seasonInvalid = computed(() => draft.value.season !== '' && !/^\d+$/.test(draft.value.season))
const episodeInvalid = computed(
  () => draft.value.episode !== '' && !/^\d+$/.test(draft.value.episode),
)
const yearInvalid = computed(() => draft.value.year !== '' && !/^\d{4}$/.test(draft.value.year))

watch(
  filtered,
  (list) => {
    if (list.length === 0) {
      activeId.value = null
      return
    }
    if (!list.some((file) => file.id === activeId.value)) {
      const preferred = list.find((file) => store.selectedSet.has(file.id))
      activeId.value = (preferred ?? list[0]).id
    }
  },
  { immediate: true },
)

watch(active, (file) => {
  error.value = ''
  if (!file) {
    draft.value = blankDraft()
    return
  }
  const parsed = file.parsed
  draft.value = {
    title: parsed?.title ?? '',
    year: parsed?.year ? String(parsed.year) : '',
    season: parsed?.season !== null && parsed?.season !== undefined ? String(parsed.season) : '',
    episode:
      parsed?.episode !== null && parsed?.episode !== undefined ? String(parsed.episode) : '',
    episode_end:
      parsed?.episode_end !== null && parsed?.episode_end !== undefined
        ? String(parsed.episode_end)
        : '',
    episode_title: parsed?.episode_title ?? '',
    resolution: parsed?.resolution ?? '',
    codec: parsed?.codec ?? '',
    release_group: parsed?.release_group ?? '',
  }
})

function valueOf(input: string): string | null {
  return input.trim() === '' ? null : input.trim()
}

function numberOf(input: string): number | null {
  return input.trim() === '' ? null : Number(input)
}

function messageOf(err: unknown) {
  return err instanceof Error ? err.message : '请求失败'
}

async function save() {
  const file = active.value
  if (!file) return
  if (titleInvalid.value) {
    error.value = '剧名不能为空，请手动填写后再保存'
    return
  }
  if (seasonInvalid.value || episodeInvalid.value) {
    error.value = '季与集必须是非负整数'
    return
  }
  if (yearInvalid.value) {
    error.value = '年份需为 4 位数字'
    return
  }
  saving.value = true
  error.value = ''
  try {
    await store.updateParse(file.id, {
      title: valueOf(draft.value.title),
      year: numberOf(draft.value.year),
      season: numberOf(draft.value.season),
      episode: numberOf(draft.value.episode),
      episode_end: numberOf(draft.value.episode_end),
      episode_title: valueOf(draft.value.episode_title),
      resolution: valueOf(draft.value.resolution),
      codec: valueOf(draft.value.codec),
      release_group: valueOf(draft.value.release_group),
    })
    toast.success('解析结果已保存')
    move(1)
  } catch (err) {
    error.value = messageOf(err)
  } finally {
    saving.value = false
  }
}

function move(offset: number) {
  const list = filtered.value
  if (list.length === 0) return
  const index = list.findIndex((file) => file.id === activeId.value)
  const next = list[(index + offset + list.length) % list.length]
  if (next) activeId.value = next.id
}

async function reparse() {
  const file = active.value
  if (!file) return
  reparsing.value = true
  error.value = ''
  try {
    await store.parse([file.id])
    toast.success('已重新解析')
  } catch (err) {
    error.value = messageOf(err)
  } finally {
    reparsing.value = false
  }
}

async function batchParse() {
  if (files.value.length === 0) return
  batchParsing.value = true
  error.value = ''
  try {
    const updated = await store.parse(files.value.map((file) => file.id))
    toast.success(`已解析 ${updated.length} 个文件`)
  } catch (err) {
    error.value = messageOf(err)
  } finally {
    batchParsing.value = false
  }
}

async function acceptAll() {
  await batchParse()
  router.push('/scrape')
}

async function copyName() {
  if (!active.value) return
  try {
    await navigator.clipboard.writeText(active.value.original_name)
    toast.info('文件名已复制')
  } catch {
    toast.error('复制失败')
  }
}

function episodeLabel(file: MediaFile): string {
  const parsed = file.parsed
  if (!parsed || parsed.episode === null) return file.original_name
  const episodeText = `E${String(parsed.episode).padStart(2, '0')}`
  return parsed.season === null
    ? episodeText
    : `S${String(parsed.season).padStart(2, '0')}${episodeText}`
}

function dotClass(file: MediaFile) {
  if (!file.parsed) return 'bg-[var(--border-strong)]'
  if (file.status === 'matched' || file.status === 'renamed') return 'bg-accent'
  if (file.confidence >= 85) return 'bg-success'
  if (file.confidence >= 60) return 'bg-warning'
  return 'bg-danger'
}

function onKeydown(event: KeyboardEvent) {
  const target = event.target as HTMLElement | null
  if (target && ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName)) return
  if (event.key === 'j') {
    event.preventDefault()
    move(1)
  } else if (event.key === 'k') {
    event.preventDefault()
    move(-1)
  }
}
onMounted(() => document.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => document.removeEventListener('keydown', onKeydown))

const tabs: { key: FilterKey; label: string }[] = [
  { key: 'all', label: '全部' },
  { key: 'todo', label: '待确认' },
  { key: 'unparsed', label: '未解析' },
]
</script>

<template>
  <div>
    <header class="mb-5 flex flex-wrap items-start gap-3">
      <div class="min-w-0 flex-1">
        <h1 class="text-2xl font-semibold leading-8 tracking-tight text-ink">解析</h1>
        <p class="mt-1 text-[13px] text-muted">检查并修正文件名解析结果，确认后再进入刮削</p>
      </div>
      <div class="flex items-center gap-2">
        <button class="btn" :disabled="batchParsing || files.length === 0" @click="batchParse">
          <AppIcon name="sparkles" :size="14" :spin="batchParsing" />
          批量自动解析
        </button>
        <button
          class="btn btn-primary"
          :disabled="batchParsing || files.length === 0"
          @click="acceptAll"
        >
          全部接受
          <AppIcon name="arrow-right" :size="14" />
        </button>
      </div>
    </header>

    <ErrorBanner v-if="error" class="mb-4" title="解析失败" :message="error" />

    <div v-if="files.length === 0" class="panel">
      <EmptyState
        icon="parse"
        title="还没有可解析的文件"
        description="请先扫描目录，扫描完成后会自动解析视频文件名。"
      >
        <button class="btn btn-primary" @click="router.push('/')">
          <AppIcon name="scan" :size="14" />
          去扫描
        </button>
      </EmptyState>
    </div>

    <div v-else class="grid items-start gap-4 lg:grid-cols-[320px_minmax(0,1fr)]">
      <section class="panel overflow-hidden">
        <div class="flex items-center gap-1 border-b border-line px-2 py-2">
          <button
            v-for="tab in tabs"
            :key="tab.key"
            class="flex h-7 items-center gap-1.5 rounded px-2 text-xs transition"
            :class="
              filter === tab.key
                ? 'bg-[var(--accent-soft)] font-medium text-accent'
                : 'text-muted hover:text-ink'
            "
            @click="filter = tab.key"
          >
            {{ tab.label }}
            <span class="font-mono text-[10.5px] opacity-70">{{ counts[tab.key] }}</span>
          </button>
        </div>

        <div class="max-h-[calc(100vh-260px)] overflow-y-auto">
          <button
            v-for="file in filtered"
            :key="file.id"
            class="flex h-12 w-full items-center gap-2.5 border-b border-line/50 px-3 text-left transition last:border-0"
            :class="
              file.id === activeId
                ? 'bg-[var(--accent-soft)]'
                : 'hover:bg-[var(--bg-elevated)]'
            "
            @click="activeId = file.id"
          >
            <span class="h-1.5 w-1.5 flex-none rounded-full" :class="dotClass(file)" />
            <span class="min-w-0 flex-1">
              <span class="block truncate font-mono text-xs text-ink">
                {{ episodeLabel(file) }}
              </span>
              <span class="block truncate text-[11px] text-faint">{{ file.parsed?.title ?? '未解析' }}</span>
            </span>
            <span v-if="file.parsed" class="flex-none font-mono text-[11px] text-muted">
              {{ file.confidence }}%
            </span>
            <AppIcon v-if="!file.parsed" name="alert" :size="12" class="flex-none text-warning" />
          </button>

          <p v-if="filtered.length === 0" class="py-10 text-center text-xs text-faint">
            该筛选下暂无文件
          </p>
        </div>
      </section>

      <section v-if="active" class="panel overflow-hidden">
        <div class="border-b border-line px-4 py-3">
          <div class="flex items-start gap-2">
            <p class="min-w-0 flex-1 break-all font-mono text-[13px] leading-5 text-ink">
              {{ active.original_name }}
            </p>
            <button class="icon-btn -mr-1.5 -mt-1 flex-none" title="复制文件名" @click="copyName">
              <AppIcon name="copy" :size="14" />
            </button>
          </div>
          <div class="mt-2 flex flex-wrap items-center gap-2 text-[11.5px] text-faint">
            <span v-if="active.parsed">置信度</span>
            <ConfidenceBadge v-if="active.parsed" :value="active.confidence" />
            <span v-else class="tag tag-warning">未解析</span>
            <span class="ml-auto font-mono">{{ activeIndex + 1 }} / {{ filtered.length }}</span>
          </div>
        </div>

        <div class="grid gap-3 p-4 sm:grid-cols-2">
          <div class="sm:col-span-2">
            <label class="label">剧名</label>
            <input
              v-model="draft.title"
              class="input"
              :class="titleInvalid ? 'border-warning' : ''"
              placeholder="例如 Breaking Bad"
            />
            <p v-if="titleInvalid" class="mt-1 text-[11.5px] text-warning">
              请手动填写剧名，否则无法匹配
            </p>
          </div>

          <div>
            <label class="label">年份</label>
            <input
              v-model="draft.year"
              class="input font-mono"
              :class="yearInvalid ? 'border-warning' : ''"
              placeholder="2008"
              inputmode="numeric"
            />
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="label">季</label>
              <input
                v-model="draft.season"
                class="input font-mono"
                :class="seasonInvalid ? 'border-danger' : ''"
                placeholder="1"
                inputmode="numeric"
              />
            </div>
            <div>
              <label class="label">集</label>
              <input
                v-model="draft.episode"
                class="input font-mono"
                :class="episodeInvalid ? 'border-danger' : ''"
                placeholder="3"
                inputmode="numeric"
              />
            </div>
          </div>

          <div class="sm:col-span-2">
            <label class="label">集标题</label>
            <input v-model="draft.episode_title" class="input" placeholder="可留空" />
          </div>

          <div>
            <label class="label">分辨率</label>
            <input v-model="draft.resolution" class="input font-mono" placeholder="1080p" />
          </div>

          <div>
            <label class="label">编码</label>
            <input v-model="draft.codec" class="input font-mono" placeholder="x264" />
          </div>

          <div>
            <label class="label">发布组</label>
            <input v-model="draft.release_group" class="input font-mono" placeholder="DEMAND" />
          </div>

          <div>
            <label class="label">结束集（可选）</label>
            <input
              v-model="draft.episode_end"
              class="input font-mono"
              placeholder="用于多集合并文件"
              inputmode="numeric"
            />
          </div>
        </div>

        <div class="flex flex-wrap items-center gap-2 border-t border-line px-4 py-3">
          <button class="btn" :disabled="reparsing || saving" @click="reparse">
            <AppIcon name="refresh" :size="14" :spin="reparsing" />
            重新自动解析
          </button>
          <button class="btn btn-ghost" :disabled="saving" @click="move(1)">跳过</button>
          <button class="btn btn-primary ml-auto" :disabled="saving" @click="save">
            <AppIcon v-if="saving" name="loader" :size="14" spin />
            保存并下一项
            <AppIcon name="arrow-right" :size="14" />
          </button>
        </div>
      </section>

      <section v-else class="panel">
        <EmptyState icon="parse" title="选择左侧文件" description="选中文件后即可查看并修正解析结果。" />
      </section>
    </div>
  </div>
</template>
