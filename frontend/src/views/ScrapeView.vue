<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { api } from '@/api/client'
import AppIcon from '@/components/AppIcon.vue'
import EmptyState from '@/components/EmptyState.vue'
import EpisodeMapper from '@/components/EpisodeMapper.vue'
import ErrorBanner from '@/components/ErrorBanner.vue'
import PageHeader from '@/components/PageHeader.vue'
import Pager from '@/components/Pager.vue'
import ShowCard from '@/components/ShowCard.vue'
import SelectMenu from '@/components/SelectMenu.vue'
import type { SlateRow } from '@/components/ui-types'
import { usePagination } from '@/composables/usePagination'
import { useRecentSearches } from '@/composables/useRecentSearches'
import { useToast } from '@/composables/useToast'
import { useWorkflowStore } from '@/stores/workflow'
import type { Episode, MediaFile, Show, ShowDetail } from '@/types'

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
const episodesBySeason = ref<Record<number, Episode[]>>({})
const detailLoading = ref(false)
const season = ref<number | null>(null)
const matching = ref(false)
const error = ref('')

const parsedFiles = computed(() => store.parsedFiles)
const { page, pageSize, total, pageCount, pageItems } = usePagination(parsedFiles)
const providers = computed(() => store.providers)
const configured = computed(
  () => providers.value.find((item) => item.name === provider.value)?.configured ?? false,
)

const targetFiles = computed(() => {
  const selected = store.selectedFiles.filter((file) => file.is_video && file.parsed)
  return selected.length > 0 ? selected : parsedFiles.value
})

const seasons = computed(() => detail.value?.seasons ?? [])
const episodes = computed(() =>
  season.value === null ? [] : (episodesBySeason.value[season.value] ?? []),
)

const mappingCount = computed(() =>
  targetFiles.value.filter((file) => {
    const parsed = file.parsed
    if (!parsed || parsed.episode === null || parsed.episode === undefined) return false
    const seasonNo = parsed.season ?? season.value ?? 1
    const list = episodesBySeason.value[seasonNo] ?? []
    return list.some((item) => item.episode === parsed.episode)
  }).length,
)

const { items: recentSearches, push: pushRecent } = useRecentSearches()

const slate = computed<SlateRow[]>(() => [
  { label: 'PROVIDER', value: provider.value.toUpperCase() },
  { label: 'MATCHED', value: `${mappingCount.value}/${targetFiles.value.length}`, tone: 'amber' },
  { label: 'SEASON', value: season.value === null ? '—' : `SEASON ${String(season.value).padStart(2, '0')}` },
  {
    label: 'STATUS',
    value:
      targetFiles.value.length - mappingCount.value > 0
        ? `${targetFiles.value.length - mappingCount.value} NEED REVIEW`
        : 'READY',
    tone: targetFiles.value.length === mappingCount.value ? 'green' : 'amber',
  },
])

function useRecent(value: string) {
  query.value = value
  void search()
}

function fileMatchState(file: MediaFile): 'match' | 'review' | 'idle' {
  const parsed = file.parsed
  if (!parsed || parsed.episode === null || parsed.episode === undefined) return 'idle'
  const seasonNo = parsed.season ?? season.value
  if (seasonNo === null) return 'idle'
  const list = episodesBySeason.value[seasonNo] ?? []
  if (list.length === 0) return 'idle'
  return list.some((item) => item.episode === parsed.episode) ? 'match' : 'review'
}

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
    pushRecent(keyword)
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

    const numbers = new Set<number>([nextSeason])
    for (const file of targetFiles.value) {
      if (file.parsed?.season !== null && file.parsed?.season !== undefined) {
        numbers.add(file.parsed.season)
      }
    }
    const wanted = [...numbers].sort((a, b) => a - b)
    const details = await Promise.all(
      wanted.map((value) => api.getShow(provider.value, show.id, value)),
    )
    const map: Record<number, Episode[]> = {}
    wanted.forEach((value, index) => {
      map[value] =
        details[index].seasons.find((item) => item.season === value)?.episodes ?? []
    })
    episodesBySeason.value = map
    detail.value = details[0] ?? base
  } catch (err) {
    error.value = messageOf(err)
    detail.value = null
    episodesBySeason.value = {}
  } finally {
    detailLoading.value = false
  }
}

async function loadSeason() {
  if (!chosen.value || season.value === null) return
  const seasonNo = season.value
  if (seasonNo in episodesBySeason.value) return
  detailLoading.value = true
  error.value = ''
  try {
    const result = await api.getShow(provider.value, chosen.value.id, seasonNo)
    episodesBySeason.value = {
      ...episodesBySeason.value,
      [seasonNo]: result.seasons.find((item) => item.season === seasonNo)?.episodes ?? [],
    }
    detail.value = result
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
    <PageHeader
      ghost="03"
      kicker="STEP 03 · SCRAPE"
      title="刮削"
      title-en="SCRAPE"
      description="从 TMDB 搜索剧集，自动对齐本地季集与目标剧集，生成 NFO 与海报。"
      :slate="slate"
    />

    <section class="panel">
      <div class="scan-controls" style="padding: 12px 14px">
        <div class="controls-main scrape-search" style="margin-top: 0">
          <div class="input-group">
            <AppIcon name="search" :size="14" />
            <input
              v-model="query"
              placeholder="输入剧名，回车搜索"
              spellcheck="false"
              aria-label="搜索剧名"
              @keydown.enter="search"
            />
          </div>

          <div class="input-group" style="width: 152px">
            <AppIcon name="film" :size="14" />
            <SelectMenu
              v-model="provider"
              class="!w-full"
              :options="providers.map((p) => ({ value: p.name, label: p.label }))"
            />
          </div>

          <button class="btn" :disabled="searching" @click="search">
            <AppIcon name="search" :size="14" :spin="searching" />
            搜索
          </button>
          <button
            class="btn btn-amber"
            :disabled="matching || !chosen || parsedFiles.length === 0"
            @click="runMatch(true)"
          >
            <AppIcon name="sparkles" :size="14" :spin="matching" />
            自动匹配全部
          </button>
        </div>
      </div>
    </section>

    <ErrorBanner v-if="error" class="mt-3" :message="error" />

    <div v-if="!configured" class="warn-note mt-3">
      <AppIcon name="alert" :size="15" />
      <span class="flex-1">尚未配置 TMDB API Key，无法搜索。请前往设置填写。</span>
      <button class="btn btn-sm flex-none" @click="router.push('/settings')">去设置</button>
    </div>

    <div v-if="parsedFiles.length === 0" class="panel mt-3">
      <EmptyState
        icon="scrape"
        title="没有可刮削的文件"
        description="请先在解析页确认文件名解析结果，再回来匹配剧集。"
      >
        <button class="btn btn-amber" @click="router.push('/parse')">
          <AppIcon name="parse" :size="14" />
          去解析
        </button>
      </EmptyState>
    </div>

    <div v-else class="scrape-grid">
      <section class="panel scrape-panel">
        <div class="panel-head">
          <span class="panel-title">PENDING <b>待匹配</b></span>
          <span class="mono dim" style="font-size: 9.5px">{{ parsedFiles.length }}</span>
        </div>

        <div class="pick-list">
          <label
            v-for="file in pageItems"
            :key="file.id"
            class="pick-row"
            :class="{ sel: store.selectedSet.has(file.id) }"
          >
            <input
              type="checkbox"
              :checked="store.selectedSet.has(file.id)"
              :aria-label="`选择 ${file.original_name}`"
              @change="toggle(file.id)"
            />
            <span class="pick-main">
              <b>
                {{
                  file.parsed?.episode != null
                    ? `S${String(file.parsed.season ?? 1).padStart(2, '0')}E${String(file.parsed.episode).padStart(2, '0')}`
                    : '未知集'
                }}
              </b>
              <small>{{ file.parsed?.episode_title ?? file.parsed?.title ?? file.original_name }}</small>
            </span>
            <span v-if="fileMatchState(file) === 'match'" class="tag tag-ok">MATCH</span>
            <span v-else-if="fileMatchState(file) === 'review'" class="tag tag-warn">REVIEW</span>
            <span v-else class="tag tag-mute">待匹配</span>
          </label>
        </div>

        <Pager
          v-if="parsedFiles.length"
          v-model:page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-count="pageCount"
          compact
        />
      </section>

      <section class="panel scrape-panel">
        <div class="panel-head">
          <span class="panel-title">CANDIDATES <b>候选剧集</b></span>
          <span class="panel-side mono dim" style="font-size: 9.5px">
            {{ results.length }} RESULTS
          </span>
        </div>

        <div v-if="searching" class="show-grid candidate-grid">
          <div
            v-for="index in 4"
            :key="index"
            class="h-[94px] animate-pulse rounded-lg border border-line bg-[var(--surface-2)]"
          />
        </div>

        <div v-else-if="results.length" class="show-grid candidate-grid">
          <ShowCard
            v-for="show in results"
            :key="show.id"
            :show="show"
            :selected="chosen?.id === show.id"
            @select="choose"
          />
        </div>

        <div v-else class="flex flex-1 items-center justify-center">
          <EmptyState
            icon="scrape"
            :title="searched ? '没有找到匹配的剧集' : '搜索剧集开始刮削'"
            :description="
              searched
                ? '换个关键词，或切换媒体源后再试。'
                : '在顶部输入剧名，选择正确的剧集后即可自动对齐季集。'
            "
          />
        </div>

        <div v-if="recentSearches.length" class="recent-searches">
          <span class="lbl">RECENT</span>
          <button
            v-for="item in recentSearches"
            :key="item"
            type="button"
            @click="useRecent(item)"
          >
            {{ item }}
          </button>
        </div>

        <div v-if="results.length" class="candidate-legend">
          <div class="legend">
            <span><i style="background: var(--amber)" />已选择</span>
            <span><i style="background: var(--line-2)" />hover 预览</span>
            <span style="margin-left: auto">ENTER 选择</span>
          </div>
        </div>
      </section>

      <section class="panel scrape-panel">
        <div class="panel-head">
          <span class="panel-title">MAPPING <b>匹配关系</b></span>
          <span class="mono dim" style="font-size: 9.5px">
            {{ mappingCount }}/{{ targetFiles.length }}
          </span>
        </div>

        <div v-if="!chosen" class="flex flex-1 items-center justify-center">
          <EmptyState icon="film" title="尚未选择剧集" description="从中间候选列表选择一部剧集。" />
        </div>

        <template v-else>
          <div class="map-head">
            <span class="poster" style="width: 42px">
              <img
                v-if="chosen.poster_url"
                :src="chosen.poster_url"
                :alt="chosen.title"
                class="h-full w-full object-cover"
              />
              <span v-else class="poster-art">
                <span class="mark" style="font-size: 24px">
                  {{ chosen.title.slice(0, 2).toUpperCase() }}
                </span>
                <span class="code">{{ chosen.year ?? '' }}</span>
              </span>
            </span>
            <div class="map-title">
              <h4>{{ chosen.title }}</h4>
              <div class="en">{{ chosen.original_title || chosen.title }}</div>
              <div class="meta">
                {{ chosen.year ?? '—' }} · ★ {{ chosen.rating?.toFixed(1) ?? '—' }} ·
                {{ chosen.seasons_count }} 季
              </div>
              <div class="select-inline">
                <label>SEASON</label>
                <SelectMenu
                  v-model="season"
                  class="!h-[24px] !w-auto min-w-[100px] text-xs"
                  :options="seasons.map((s) => ({ value: s.season, label: s.name || `第 ${s.season} 季` }))"
                />
              </div>
            </div>
          </div>

          <div class="min-h-0 flex-1 overflow-y-auto">
            <EpisodeMapper
              v-if="episodes.length"
              :files="targetFiles"
              :episodes-by-season="episodesBySeason"
              :season="season"
            />
            <div v-else-if="detailLoading" class="space-y-2 p-3">
              <div v-for="index in 5" :key="index" class="h-9 animate-pulse rounded bg-[var(--surface-2)]" />
            </div>
            <div v-else class="flex h-full items-center justify-center">
              <EmptyState icon="film" title="该季暂无剧集信息" description="请切换季或换一部剧集。" />
            </div>
          </div>

          <div class="map-foot">
            <button class="btn btn-amber" :disabled="matching" @click="runMatch(false)">
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
