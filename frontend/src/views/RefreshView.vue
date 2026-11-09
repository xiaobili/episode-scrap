<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { api } from '@/api/client'
import AppIcon from '@/components/AppIcon.vue'
import EmptyState from '@/components/EmptyState.vue'
import ErrorBanner from '@/components/ErrorBanner.vue'
import StatusTag from '@/components/StatusTag.vue'
import { useToast } from '@/composables/useToast'
import { useWorkflowStore } from '@/stores/workflow'
import type { JellyfinLibrary } from '@/types'

const store = useWorkflowStore()
const router = useRouter()
const toast = useToast()

const libraries = ref<JellyfinLibrary[]>([])
const selected = ref<string[]>([])
const loading = ref(false)
const refreshing = ref(false)
const results = ref<Record<string, { ok: boolean; error: string | null }>>({})
const error = ref('')

const configured = computed(() =>
  Boolean(store.settings?.jellyfin_url && store.settings?.has_jellyfin_key),
)
const allChosen = computed(
  () => libraries.value.length > 0 && selected.value.length === libraries.value.length,
)

function typeLabel(type: string | null) {
  if (type === 'tvshows') return '剧集'
  if (type === 'movies') return '电影'
  if (type === 'music') return '音乐'
  return type ?? '混合'
}

function messageOf(err: unknown) {
  return err instanceof Error ? err.message : '请求失败'
}

async function loadLibraries() {
  if (!configured.value) return
  loading.value = true
  error.value = ''
  try {
    libraries.value = await api.getJellyfinLibraries()
    selected.value = []
    results.value = {}
  } catch (err) {
    error.value = messageOf(err)
  } finally {
    loading.value = false
  }
}

function toggle(id: string) {
  selected.value = selected.value.includes(id)
    ? selected.value.filter((item) => item !== id)
    : [...selected.value, id]
}

function toggleAll() {
  selected.value = allChosen.value ? [] : libraries.value.map((lib) => lib.id)
}

async function refresh() {
  if (selected.value.length === 0) {
    error.value = '请选择要刷新的媒体库'
    return
  }
  refreshing.value = true
  error.value = ''
  results.value = {}
  try {
    const response = await api.refreshJellyfinLibraries(selected.value)
    const map: Record<string, { ok: boolean; error: string | null }> = {}
    let failed = 0
    for (const item of response.results) {
      map[item.library_id] = { ok: item.ok, error: item.error }
      if (!item.ok) failed += 1
    }
    results.value = map
    if (failed === 0) toast.success(`已触发 ${response.results.length} 个媒体库刷新`)
    else toast.error(`${failed} 个媒体库刷新失败`)
  } catch (err) {
    error.value = messageOf(err)
  } finally {
    refreshing.value = false
  }
}

onMounted(loadLibraries)
</script>

<template>
  <div>
    <header class="mb-5">
      <h1 class="text-2xl font-semibold leading-8 tracking-tight text-ink">刷新媒体库</h1>
      <p class="mt-1 text-[13px] text-muted">重命名完成后，通知 Jellyfin 扫描指定媒体库</p>
    </header>

    <ErrorBanner v-if="error" class="mb-4" :message="error" />

    <div v-if="!configured" class="panel">
      <EmptyState
        icon="server"
        title="尚未配置 Jellyfin"
        description="先在设置中填写 Jellyfin 服务器地址与 API Key。"
      >
        <button class="btn btn-primary" @click="router.push('/settings')">
          <AppIcon name="settings" :size="14" />
          去设置
        </button>
      </EmptyState>
    </div>

    <section v-else class="panel overflow-hidden">
      <div class="flex flex-wrap items-center gap-2 border-b border-line px-4 py-3">
        <button class="btn" :disabled="loading" @click="loadLibraries">
          <AppIcon name="refresh" :size="14" :spin="loading" />
          重新加载
        </button>
        <span v-if="libraries.length" class="text-[11.5px] text-faint">
          共 {{ libraries.length }} 个媒体库，已选 {{ selected.length }} 个
        </span>
        <button
          class="btn btn-primary ml-auto"
          :disabled="refreshing || selected.length === 0"
          @click="refresh"
        >
          <AppIcon name="play" :size="14" />
          刷新选中（{{ selected.length }}）
        </button>
      </div>

      <div v-if="loading" class="space-y-2 p-4">
        <div
          v-for="index in 3"
          :key="index"
          class="h-12 animate-pulse rounded-lg border border-line bg-[var(--bg-elevated)]"
        />
      </div>

      <div v-else-if="libraries.length === 0" class="px-4">
        <EmptyState
          icon="database"
          title="未获取到媒体库"
          description="请确认 Jellyfin 服务可达，且 API Key 有读取媒体库的权限。"
        />
      </div>

      <div v-else class="divide-y divide-line/60">
        <label
          class="flex h-11 cursor-pointer select-none items-center gap-3 border-b border-line px-4 text-xs text-faint"
        >
          <input
            type="checkbox"
            class="h-4 w-4 accent-accent"
            :checked="allChosen"
            aria-label="全选媒体库"
            @change="toggleAll"
          />
          全选
        </label>
        <div
          v-for="lib in libraries"
          :key="lib.id"
          class="flex items-center gap-3 px-4 py-3"
        >
          <input
            type="checkbox"
            class="h-4 w-4 flex-none accent-accent"
            :checked="selected.includes(lib.id)"
            :aria-label="`选择 ${lib.name}`"
            @change="toggle(lib.id)"
          />
          <span class="flex h-8 w-8 flex-none items-center justify-center rounded-md bg-[var(--bg-elevated)] text-accent">
            <AppIcon name="film" :size="15" />
          </span>
          <div class="min-w-0 flex-1">
            <p class="truncate text-[13px] font-medium text-ink">{{ lib.name }}</p>
            <p class="text-[11.5px] text-faint">{{ typeLabel(lib.collection_type) }}</p>
          </div>
          <template v-if="results[lib.id]">
            <span v-if="results[lib.id].error" class="max-w-48 truncate text-[11px] text-danger" :title="results[lib.id].error ?? ''">
              {{ results[lib.id].error }}
            </span>
            <StatusTag
              :status="results[lib.id].ok ? 'success' : 'failed'"
              :text="results[lib.id].ok ? '已触发' : '失败'"
            />
          </template>
        </div>
      </div>
    </section>

    <div class="mt-4 flex items-center justify-between gap-2">
      <button class="btn btn-ghost" @click="router.push('/rename')">
        <AppIcon name="arrow-left" :size="14" />
        上一步
      </button>
      <span class="text-[11.5px] text-faint">
        刷新为异步操作，Jellyfin 扫描进度请在其控制台查看
      </span>
    </div>
  </div>
</template>
