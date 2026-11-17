<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import AppIcon from '@/components/AppIcon.vue'
import ConfidenceGauge from '@/components/ConfidenceGauge.vue'
import EmptyState from '@/components/EmptyState.vue'
import ErrorBanner from '@/components/ErrorBanner.vue'
import PageHeader from '@/components/PageHeader.vue'
import Pager from '@/components/Pager.vue'
import type { SlateRow } from '@/components/ui-types'
import { usePagination } from '@/composables/usePagination'
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

const avgConfidence = computed(() => {
  const parsed = files.value.filter((file) => file.parsed)
  if (parsed.length === 0) return null
  return Math.round(parsed.reduce((sum, file) => sum + file.confidence, 0) / parsed.length)
})

const slate = computed<SlateRow[]>(() => [
  { label: 'FILES', value: String(files.value.length) },
  { label: 'PENDING', value: String(counts.value.todo), tone: counts.value.todo ? 'amber' : undefined },
  {
    label: 'AVG CONF.',
    value: avgConfidence.value === null ? '—' : `${avgConfidence.value}%`,
    tone: avgConfidence.value !== null && avgConfidence.value >= 85 ? 'green' : 'amber',
  },
  { label: 'MODE', value: 'MANUAL REVIEW' },
])

const filtered = computed(() => {
  if (filter.value === 'todo') return files.value.filter(needsReview)
  if (filter.value === 'unparsed') return files.value.filter((file) => !file.parsed)
  return files.value
})

const active = computed(() => files.value.find((file) => file.id === activeId.value) ?? null)
const activeIndex = computed(() => filtered.value.findIndex((file) => file.id === activeId.value))

const { page, pageSize, total, pageCount, pageItems } = usePagination(filtered)

watch(filter, () => {
  page.value = 1
})

watch(activeId, () => {
  const index = filtered.value.findIndex((file) => file.id === activeId.value)
  if (index >= 0) page.value = Math.floor(index / pageSize.value) + 1
})

watch(page, () => {
  if (!pageItems.value.some((file) => file.id === activeId.value) && pageItems.value[0]) {
    activeId.value = pageItems.value[0].id
  }
})

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
  if (!file.parsed) return ''
  if (file.status === 'matched' || file.status === 'renamed') return 'ok'
  if (file.confidence >= 85) return 'ok'
  if (file.confidence >= 60) return 'warn'
  return 'bad'
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
    <PageHeader
      ghost="02"
      kicker="STEP 02 · PARSE"
      title="解析"
      title-en="PARSE"
      description="检查并修正文件名解析结果，确认剧名、季集与发布信息后再进入刮削。"
      :slate="slate"
    >
      <template #actions>
        <button class="btn" :disabled="batchParsing || files.length === 0" @click="batchParse">
          <AppIcon name="sparkles" :size="14" :spin="batchParsing" />
          批量自动解析
        </button>
        <button
          class="btn btn-amber"
          :disabled="batchParsing || files.length === 0"
          @click="acceptAll"
        >
          全部接受
          <AppIcon name="arrow-right" :size="14" />
        </button>
      </template>
    </PageHeader>

    <ErrorBanner v-if="error" class="mb-4" title="解析失败" :message="error" />

    <div v-if="files.length === 0" class="panel">
      <EmptyState
        icon="parse"
        title="还没有可解析的文件"
        description="请先扫描目录，扫描完成后会自动解析视频文件名。"
      >
        <button class="btn btn-amber" @click="router.push('/')">
          <AppIcon name="scan" :size="14" />
          去扫描
        </button>
      </EmptyState>
    </div>

    <div v-else class="split-parse">
      <section class="panel">
        <div class="panel-head">
          <span class="panel-title">FILE ROLL <b>文件卷</b></span>
          <span class="mono dim" style="font-size: 9.5px">{{ filtered.length }}</span>
        </div>

        <div class="tabs-line">
          <button
            v-for="tab in tabs"
            :key="tab.key"
            class="tab"
            :class="{ on: filter === tab.key }"
            @click="filter = tab.key"
          >
            {{ tab.label }} {{ counts[tab.key] }}
          </button>
        </div>

        <div class="roll">
          <button
            v-for="file in pageItems"
            :key="file.id"
            class="roll-item"
            :class="{ on: file.id === activeId }"
            @click="activeId = file.id"
          >
            <span class="dot" :class="dotClass(file)" />
            <span class="roll-main">
              <b>{{ episodeLabel(file) }}</b>
              <small>{{ file.parsed?.title ?? '未解析' }}</small>
            </span>
            <span class="conf">{{ file.parsed ? `${file.confidence}%` : '未解析' }}</span>
          </button>

          <p v-if="filtered.length === 0" class="py-10 text-center text-xs text-faint">
            该筛选下暂无文件
          </p>
        </div>

        <div class="roll-foot">
          <span class="kbd">J</span><span class="kbd">K</span> 切换
        </div>

        <Pager
          v-if="filtered.length"
          v-model:page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-count="pageCount"
        />
      </section>

      <section v-if="active" class="panel">
        <div class="shot-head">
          <div class="shot-id">
            <span class="badge">{{ episodeLabel(active) }}</span>
            <small>SHOT DETAIL / 解析详情</small>
          </div>
          <div class="flex items-center gap-2">
            <button class="btn btn-sm btn-ghost" :disabled="reparsing || saving" @click="reparse">
              <AppIcon name="refresh" :size="13" :spin="reparsing" />
              重新自动解析
            </button>
            <button class="btn btn-sm btn-ghost" :disabled="saving" @click="move(1)">跳过</button>
          </div>
        </div>

        <div class="raw-block">
          <span class="lbl">RAW FILE</span>
          <code>{{ active.original_name }}</code>
          <button class="copy" title="复制文件名" @click="copyName">
            <AppIcon name="copy" :size="14" />
          </button>
        </div>

        <div class="detail-grid">
          <div class="form-grid">
            <div class="field span-2" :class="{ low: titleInvalid }">
              <label>剧名 <span>TITLE</span></label>
              <input v-model="draft.title" class="input mono" placeholder="例如 Breaking Bad" />
              <div v-if="titleInvalid" class="hint-low">请手动填写剧名，否则无法匹配</div>
            </div>

            <div class="field" :class="{ low: yearInvalid }">
              <label>年份 <span>YEAR</span></label>
              <input
                v-model="draft.year"
                class="input mono"
                placeholder="2008"
                inputmode="numeric"
              />
            </div>

            <div class="field" :class="{ low: seasonInvalid || episodeInvalid }">
              <label>季 / 集 <span>SEASON / EPISODE</span></label>
              <div class="flex items-center gap-2">
                <input
                  v-model="draft.season"
                  class="input mono"
                  placeholder="1"
                  inputmode="numeric"
                />
                <span class="mono dim text-[10px]">/</span>
                <input
                  v-model="draft.episode"
                  class="input mono"
                  placeholder="3"
                  inputmode="numeric"
                />
              </div>
            </div>

            <div class="field span-2" :class="{ low: active.confidence < 60 }">
              <label>集标题 <span>EPISODE TITLE</span></label>
              <input v-model="draft.episode_title" class="input mono" placeholder="可留空" />
              <div v-if="active.confidence < 60" class="hint-low">
                置信度偏低，请核对原文拼写
              </div>
            </div>

            <div class="field">
              <label>分辨率 <span>RESOLUTION</span></label>
              <input v-model="draft.resolution" class="input mono" placeholder="1080p" />
            </div>

            <div class="field">
              <label>编码 <span>CODEC</span></label>
              <input v-model="draft.codec" class="input mono" placeholder="x264" />
            </div>

            <div class="field span-2">
              <label>发布组 <span>RELEASE GROUP</span></label>
              <input v-model="draft.release_group" class="input mono" placeholder="DEMAND" />
            </div>

            <div class="field">
              <label>结束集 <span>EPISODE END</span></label>
              <input
                v-model="draft.episode_end"
                class="input mono"
                placeholder="可选"
                inputmode="numeric"
              />
            </div>
          </div>

          <ConfidenceGauge v-if="active.parsed" :value="active.confidence" />
          <aside v-else class="conf-card">
            <div class="conf-label">未解析</div>
            <div class="conf-sub">NO CONFIDENCE</div>
            <p class="text-[11px] text-faint">请先执行自动解析，或手动填写字段。</p>
          </aside>
        </div>

        <div class="action-bar">
          <button class="btn btn-ghost" :disabled="reparsing || saving" @click="reparse">
            重新解析
          </button>
          <span class="mono dim" style="font-size: 9px">
            {{ activeIndex + 1 }} / {{ filtered.length }}
          </span>
          <button class="btn btn-amber push" :disabled="saving" @click="save">
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
