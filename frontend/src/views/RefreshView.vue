<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { api } from '@/api/client'
import AppIcon from '@/components/AppIcon.vue'
import EmptyState from '@/components/EmptyState.vue'
import ErrorBanner from '@/components/ErrorBanner.vue'
import PageHeader from '@/components/PageHeader.vue'
import StatusTag from '@/components/StatusTag.vue'
import ToggleSwitch from '@/components/ToggleSwitch.vue'
import type { SlateRow } from '@/components/ui-types'
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
const lastRun = ref('')
const logs = ref<{ time: string; ok: boolean; message: string }[]>([])

const configured = computed(() =>
  Boolean(store.settings?.jellyfin_url && store.settings?.has_jellyfin_key),
)

const slate = computed<SlateRow[]>(() => [
  { label: 'JELLYFIN', value: store.settings?.jellyfin_url || '—' },
  { label: 'LIBRARIES', value: String(libraries.value.length) },
  { label: 'LAST RUN', value: lastRun.value || '—' },
  {
    label: 'STATE',
    value: configured.value ? 'CONNECTED' : 'UNCONFIGURED',
    tone: configured.value ? 'green' : 'amber',
  },
])
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

function libraryName(id: string) {
  return libraries.value.find((library) => library.id === id)?.name ?? id
}

async function refresh(ids: string[] = selected.value) {
  if (ids.length === 0) {
    error.value = '请选择要刷新的媒体库'
    return
  }
  refreshing.value = true
  error.value = ''
  results.value = {}
  try {
    const response = await api.refreshJellyfinLibraries(ids)
    const map: Record<string, { ok: boolean; error: string | null }> = {}
    const time = new Date().toLocaleTimeString()
    let failed = 0
    for (const item of response.results) {
      map[item.library_id] = { ok: item.ok, error: item.error }
      if (!item.ok) failed += 1
      logs.value.unshift({
        time,
        ok: item.ok,
        message: item.ok
          ? `${libraryName(item.library_id)} 刷新已触发`
          : `${libraryName(item.library_id)} 刷新失败：${item.error ?? '未知错误'}`,
      })
    }
    results.value = map
    lastRun.value = time
    if (failed === 0) toast.success(`已触发 ${response.results.length} 个媒体库刷新`)
    else toast.error(`${failed} 个媒体库刷新失败`)
  } catch (err) {
    error.value = messageOf(err)
    logs.value.unshift({
      time: new Date().toLocaleTimeString(),
      ok: false,
      message: `刷新请求失败：${error.value}`,
    })
  } finally {
    refreshing.value = false
  }
}

function refreshOne(id: string) {
  void refresh([id])
}

onMounted(loadLibraries)
</script>

<template>
  <div>
    <PageHeader
      ghost="06"
      kicker="MAINTENANCE · REFRESH"
      title="刷新媒体库"
      title-en="REFRESH"
      description="重命名与刮削完成后，触发 Jellyfin 扫描以同步元数据、海报与 STRM。"
      :slate="slate"
    />

    <ErrorBanner v-if="error" class="mb-4" :message="error" />

    <div v-if="!configured" class="panel">
      <EmptyState
        icon="server"
        title="尚未配置 Jellyfin"
        description="先在设置中填写 Jellyfin 服务器地址与 API Key。"
      >
        <button class="btn btn-amber" @click="router.push('/settings')">
          <AppIcon name="settings" :size="14" />
          去设置
        </button>
      </EmptyState>
    </div>

    <template v-else>
      <section class="panel">
        <div class="table-toolbar">
          <div class="toolbar-title">
            <span>LIBRARIES</span>
            <b>{{ libraries.length }} FOUND</b>
            <span class="tag tag-amber">{{ selected.length }} SELECTED</span>
          </div>
          <div class="toolbar-right">
            <button class="btn btn-sm" :disabled="loading" @click="loadLibraries">
              <AppIcon name="refresh" :size="13" :spin="loading" />
              重新加载
            </button>
            <button class="btn btn-sm" :disabled="loading || !libraries.length" @click="toggleAll">
              {{ allChosen ? '取消全选' : '全选' }}
            </button>
            <button
              class="btn btn-sm btn-amber"
              :disabled="refreshing || selected.length === 0"
              @click="refresh()"
            >
              <AppIcon name="play" :size="13" :spin="refreshing" />
              刷新选中（{{ selected.length }}）
            </button>
          </div>
        </div>
      </section>

      <div v-if="loading" class="lib-grid mt-3.5">
        <div
          v-for="index in 3"
          :key="index"
          class="h-32 animate-pulse rounded-lg border border-line bg-[var(--surface-2)]"
        />
      </div>

      <div v-else-if="libraries.length === 0" class="panel mt-3.5">
        <EmptyState
          icon="database"
          title="未获取到媒体库"
          description="请确认 Jellyfin 服务可达，且 API Key 有读取媒体库的权限。"
        />
      </div>

      <div v-else class="lib-grid mt-3.5">
        <section v-for="lib in libraries" :key="lib.id" class="panel lib-card">
          <div class="k">LIBRARY / {{ typeLabel(lib.collection_type) }}</div>
          <h3>{{ lib.name }}</h3>
          <div class="last">
            {{ selected.includes(lib.id) ? 'SELECTED' : 'READY' }}
            <template v-if="results[lib.id]">
              · {{ results[lib.id].ok ? 'TRIGGERED' : 'FAILED' }}
            </template>
          </div>
          <div class="flex items-center gap-2">
            <ToggleSwitch
              :model-value="selected.includes(lib.id)"
              label="选择"
              size="sm"
              @update:model-value="toggle(lib.id)"
            />
            <button
              class="btn btn-sm btn-amber ml-auto"
              :disabled="refreshing"
              @click="refreshOne(lib.id)"
            >
              <AppIcon name="refresh" :size="13" />
              刷新媒体库
            </button>
          </div>
          <div v-if="results[lib.id]" class="mt-2 flex items-center gap-2">
            <StatusTag
              :status="results[lib.id].ok ? 'success' : 'failed'"
              :text="results[lib.id].ok ? '已触发' : '失败'"
            />
            <span
              v-if="results[lib.id].error"
              class="min-w-0 truncate text-[10.5px] text-danger"
              :title="results[lib.id].error ?? ''"
            >
              {{ results[lib.id].error }}
            </span>
          </div>
        </section>
      </div>

      <section class="panel log-panel">
        <div class="panel-head">
          <span class="panel-title">REFRESH LOG <b>刷新日志</b></span>
          <span class="mono dim" style="font-size: 9px">/api/jellyfin/refresh</span>
        </div>

        <div v-if="!logs.length" class="px-4">
          <EmptyState
            icon="clock"
            title="暂无刷新记录"
            description="触发刷新后，本次会话的结果会记录在这里。"
          />
        </div>

        <div v-else class="log-list">
          <div v-for="(entry, index) in logs" :key="index" class="log-line">
            <time>{{ entry.time }}</time>
            <span class="lvl" :class="entry.ok ? 'ok' : 'warn'">
              {{ entry.ok ? 'OK' : 'FAIL' }}
            </span>
            <span class="msg" :title="entry.message">{{ entry.message }}</span>
          </div>
        </div>
      </section>
    </template>

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
