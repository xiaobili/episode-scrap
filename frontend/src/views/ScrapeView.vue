<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { api } from '@/api/client'
import AppIcon from '@/components/AppIcon.vue'
import EmptyState from '@/components/EmptyState.vue'
import EpisodeMapper from '@/components/EpisodeMapper.vue'
import ErrorBanner from '@/components/ErrorBanner.vue'
import ShowCard from '@/components/ShowCard.vue'
import StatusTag from '@/components/StatusTag.vue'
import { useToast } from '@/composables/useToast'
import { useWorkflowStore } from '@/stores/workflow'
import type { Show, ShowDetail } from '@/types'

const store = useWorkflowStore()
const router = useRouter()
const toast = useToast()

const provider = ref('tmdb')
const query = ref('')
const results = ref<Show[]>([])
const searching = ref(false)
const searched = ref(false)
const chosen = ref<Show | null>(null)
const detail = ref<ShowDetail | null>(null)
const detailLoading = ref(false)
const season = ref<number | null>(null)
const matching = ref(false)
const error = ref('')

const parsedFiles = computed(() => store.parsedFiles)
const providers = computed(() => store.providers)
const configured = computed(
  () => providers.value.find((item) => item.name === provider.value)?.configured ?? false,
)

const targetFiles = computed(() => {
  const selected = store.selectedFiles.filter((file) => file.is_video && file.parsed)
  return selected.length > 0 ? selected : parsedFiles.value
})

const seasons = computed(() => detail.value?.seasons ?? [])
const episodes = computed(
  () => seasons.value.find((item) => item.season === season.value)?.episodes ?? [],
)

const mappingCount = computed(() => {
  const set = new Set(episodes.value.map((item) => item.episode))
  return targetFiles.value.filter((file) => {
    const value = file.parsed?.episode
    return value !== null && value !== undefined && set.has(value)
  }).length
})

function messageOf(err: unknown) {
  return err instanceof Error ? err.message : '请求失败'
}

async function search() {
  const keyword = query.value.trim()
  if (!keyword || searching.value) return
  if (!configured.value) {
    error.value = '当前媒体源尚未配置 API Key，请前往设置填写'
    return
  }
  searching.value = true
  error.value = ''
  searched.value = true
  try {
    results.value = await api.search({ query: keyword, provider: provider.value })
  } catch (err) {
    error.value = messageOf(err)
    results.value = []
  } finally {
    searching.value = false
  }
}

async function choose(show: Show) {
  chosen.value = show
  detailLoading.value = true
  error.value = ''
  try {
    const base = await api.getShow(provider.value, show.id)
    const preferred = targetFiles.value[0]?.parsed?.season
    const nextSeason =
      base.seasons.find((item) => item.season === preferred)?.season ??
      base.seasons[0]?.season ??
      1
    season.value = nextSeason
    detail.value = await api.getShow(provider.value, show.id, nextSeason)
  } catch (err) {
    error.value = messageOf(err)
    detail.value = null
  } finally {
    detailLoading.value = false
  }
}

async function loadSeason() {
  if (!chosen.value || season.value === null) return
  detailLoading.value = true
  error.value = ''
  try {
    detail.value = await api.getShow(provider.value, chosen.value.id, season.value)
  } catch (err) {
    error.value = messageOf(err)
  } finally {
    detailLoading.value = false
  }
}

async function runMatch(all = false) {
  if (!chosen.value || season.value === null) {
    error.value = '请先选择剧集并指定季'
    return
  }
  const ids = (all ? parsedFiles.value : targetFiles.value).map((file) => file.id)
  if (ids.length === 0) {
    error.value = '没有可匹配的文件'
    return
  }
  matching.value = true
  error.value = ''
  try {
    const response = await api.match({
      file_ids: ids,
      provider: provider.value,
      show_id: chosen.value.id,
      season: season.value,
    })
    await store.refreshFiles()
    toast.success(
      `匹配完成：成功 ${response.matched.length}，未匹配 ${response.unmatched.length}`,
    )
  } catch (err) {
    error.value = messageOf(err)
  } finally {
    matching.value = false
  }
}

function toggle(fileId: number) {
  store.toggleSelected(fileId)
}

onMounted(() => {
  const first = parsedFiles.value[0]?.parsed
  if (first?.title) query.value = first.title
})
</script>

<template>
  <div>
    <header class="mb-4">
      <h1 class="text-2xl font-semibold leading-8 tracking-tight text-ink">刮削</h1>
      <p class="mt-1 text-[13px] text-muted">搜索剧集并建立季集匹配关系</p>
    </header>

    <div class="mb-4 flex flex-wrap items-center gap-2">
      <div class="relative min-w-[220px] flex-1 sm:max-w-md">
        <AppIcon
          name="search"
          :size="14"
          class="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-faint"
        />
        <input
          v-model="query"
          class="input pl-8"
          placeholder="输入剧名，回车搜索"
          spellcheck="false"
          @keydown.enter="search"
        />
      </div>

      <select v-model="provider" class="select !w-auto min-w-[120px]">
        <option v-for="item in providers" :key="item.name" :value="item.name">
          {{ item.label }}
        </option>
      </select>

      <button class="btn" :disabled="searching" @click="search">
        <AppIcon name="search" :size="14" :spin="searching" />
        搜索
      </button>
      <button
        class="btn btn-primary"
        :disabled="matching || !chosen || parsedFiles.length === 0"
        @click="runMatch(true)"
      >
        <AppIcon name="sparkles" :size="14" :spin="matching" />
        自动匹配全部
      </button>
    </div>

    <ErrorBanner v-if="error" class="mb-4" :message="error" />

    <div
      v-if="!configured"
      class="mb-4 flex items-center gap-2 rounded-lg border border-[rgba(245,184,73,.35)] bg-[rgba(245,184,73,.08)] px-3.5 py-2.5 text-[13px] text-muted"
    >
      <AppIcon name="alert" :size="15" class="flex-none text-warning" />
      <span class="flex-1">尚未配置 TMDB API Key，无法搜索。请前往设置填写。</span>
      <button class="btn btn-sm flex-none" @click="router.push('/settings')">去设置</button>
    </div>

    <div v-if="parsedFiles.length === 0" class="panel">
      <EmptyState
        icon="scrape"
        title="没有可刮削的文件"
        description="请先在解析页确认文件名解析结果，再回来匹配剧集。"
      >
        <button class="btn btn-primary" @click="router.push('/parse')">
          <AppIcon name="parse" :size="14" />
          去解析
        </button>
      </EmptyState>
    </div>

    <div v-else class="grid items-start gap-4 xl:grid-cols-[280px_minmax(0,1fr)_360px]">
      <section class="panel overflow-hidden">
        <div class="flex items-center justify-between border-b border-line px-3 py-2">
          <span class="text-xs font-medium text-muted">
            待匹配 <span class="font-mono text-ink">{{ parsedFiles.length }}</span>
          </span>
          <button
            v-if="store.selectedIds.length"
            class="text-[11px] text-accent hover:underline"
            @click="store.clearSelection"
          >
            清空已选
          </button>
        </div>
        <div class="max-h-[calc(100vh-300px)] overflow-y-auto">
          <div
            v-for="file in parsedFiles"
            :key="file.id"
            class="flex h-12 cursor-pointer items-center gap-2 border-b border-line/50 px-3 transition last:border-0"
            :class="
              store.selectedSet.has(file.id)
                ? 'bg-[var(--accent-soft)]'
                : 'hover:bg-[var(--bg-elevated)]'
            "
            @click="toggle(file.id)"
          >
            <input
              type="checkbox"
              class="h-3.5 w-3.5 flex-none accent-accent"
              :checked="store.selectedSet.has(file.id)"
              @click.stop
              @change="toggle(file.id)"
            />
            <span class="min-w-0 flex-1">
              <span class="block truncate font-mono text-xs text-ink">
                {{
                  file.parsed?.episode != null
                    ? `S${String(file.parsed.season ?? 1).padStart(2, '0')}E${String(file.parsed.episode).padStart(2, '0')}`
                    : '未知集'
                }}
              </span>
              <span class="block truncate text-[11px] text-faint">
                {{ file.parsed?.episode_title ?? file.parsed?.title }}
              </span>
            </span>
            <StatusTag :status="file.status" />
          </div>
        </div>
      </section>

      <section class="panel overflow-hidden">
        <div class="flex items-center justify-between border-b border-line px-3 py-2">
          <span class="text-xs font-medium text-muted">
            候选剧集
            <span class="ml-1 font-mono text-ink">{{ results.length }}</span>
          </span>
          <span v-if="searched && !searching" class="text-[11px] text-faint">来源 {{ provider.toUpperCase() }}</span>
        </div>

        <div v-if="searching" class="grid gap-2 p-3 sm:grid-cols-2">
          <div
            v-for="index in 4"
            :key="index"
            class="h-[94px] animate-pulse rounded-lg border border-line bg-[var(--bg-elevated)]"
          />
        </div>

        <div v-else-if="results.length" class="grid max-h-[calc(100vh-300px)] gap-2 overflow-y-auto p-3 sm:grid-cols-2">
          <ShowCard
            v-for="show in results"
            :key="show.id"
            :show="show"
            :selected="chosen?.id === show.id"
            @select="choose"
          />
        </div>

        <EmptyState
          v-else
          icon="scrape"
          :title="searched ? '没有找到匹配的剧集' : '搜索剧集开始刮削'"
          :description="
            searched
              ? '换个关键词，或切换媒体源后再试。'
              : '在顶部输入剧名，选择正确的剧集后即可自动对齐季集。'
          "
        />
      </section>

      <section class="panel flex flex-col overflow-hidden">
        <div class="flex items-center justify-between border-b border-line px-3 py-2">
          <span class="text-xs font-medium text-muted">匹配关系</span>
          <span class="font-mono text-[11px] text-faint">
            {{ mappingCount }}/{{ targetFiles.length }}
          </span>
        </div>

        <div v-if="!chosen" class="flex-1">
          <EmptyState icon="film" title="尚未选择剧集" description="从中间候选列表选择一部剧集。" />
        </div>

        <template v-else>
          <div class="flex items-start gap-3 border-b border-line px-3 py-3">
            <span
              class="grid h-[66px] w-11 flex-none place-items-center overflow-hidden rounded border border-line bg-base text-faint"
            >
              <img
                v-if="chosen.poster_url"
                :src="chosen.poster_url"
                :alt="chosen.title"
                class="h-full w-full object-cover"
              />
              <AppIcon v-else name="film" :size="16" />
            </span>
            <div class="min-w-0 flex-1">
              <p class="truncate text-[13px] font-medium text-ink">{{ chosen.title }}</p>
              <p class="mt-0.5 text-[11.5px] text-faint">
                {{ chosen.year ?? '—' }} · {{ chosen.seasons_count }} 季
              </p>
              <div class="mt-1.5 flex items-center gap-1.5">
                <label class="text-[11px] text-muted">季</label>
                <select v-model.number="season" class="select h-7 !w-auto min-w-[100px] text-xs" @change="loadSeason">
                  <option v-for="item in seasons" :key="item.season" :value="item.season">
                    {{ item.name || `第 ${item.season} 季` }}
                  </option>
                </select>
              </div>
            </div>
          </div>

          <div class="min-h-0 flex-1">
            <EpisodeMapper
              v-if="episodes.length"
              :files="targetFiles"
              :episodes="episodes"
              :season="season"
            />
            <div v-else-if="detailLoading" class="space-y-2 p-3">
              <div v-for="index in 5" :key="index" class="h-9 animate-pulse rounded bg-[var(--bg-elevated)]" />
            </div>
            <EmptyState v-else icon="film" title="该季暂无剧集信息" description="请切换季或换一部剧集。" />
          </div>

          <div class="border-t border-line px-3 py-2.5">
            <button class="btn btn-primary w-full" :disabled="matching" @click="runMatch(false)">
              <AppIcon v-if="matching" name="loader" :size="14" spin />
              确认匹配 {{ targetFiles.length }} 项
            </button>
          </div>
        </template>
      </section>
    </div>

    <div v-if="parsedFiles.length" class="mt-4 flex items-center justify-end gap-2">
      <button class="btn btn-ghost" @click="router.push('/parse')">
        <AppIcon name="arrow-left" :size="14" />
        上一步
      </button>
      <button class="btn" @click="router.push('/rename')">
        下一步：重命名
        <AppIcon name="arrow-right" :size="14" />
      </button>
    </div>
  </div>
</template>
