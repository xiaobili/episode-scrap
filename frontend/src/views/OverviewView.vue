<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { api } from '@/api/client'
import AppIcon from '@/components/AppIcon.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import EmptyState from '@/components/EmptyState.vue'
import ErrorBanner from '@/components/ErrorBanner.vue'
import PageHeader from '@/components/PageHeader.vue'
import StatStrip from '@/components/StatStrip.vue'
import StatusTag from '@/components/StatusTag.vue'
import type { SlateRow, StatItem } from '@/components/ui-types'
import { useToast } from '@/composables/useToast'
import { useWorkflowStore } from '@/stores/workflow'
import type { Task } from '@/types'

interface Stage {
  key: string
  num: string
  label: string
  en: string
  icon: string
  count: number
  sub: string
  percent: number
  route: string
}

const store = useWorkflowStore()
const router = useRouter()
const toast = useToast()

const tasks = ref<Task[]>([])
const error = ref('')
const syncing = ref(false)
const rollbackOpen = ref(false)
const rollingBack = ref(false)

let timer: number | undefined
let hadActive = false

const videoCount = computed(() => store.videoFiles.length)
const parsedCount = computed(() => store.parsedFiles.length)
const matchedCount = computed(() => store.matchedFiles.length)
const renamedCount = computed(
  () => store.videoFiles.filter((file) => file.status === 'renamed').length,
)
const inQueue = computed(
  () =>
    store.parsedFiles.filter(
      (file) => file.status !== 'matched' && file.status !== 'renamed',
    ).length,
)
const pendingParse = computed(() => Math.max(0, videoCount.value - parsedCount.value))
const pendingScrape = computed(() => Math.max(0, parsedCount.value - matchedCount.value))
const pendingRename = computed(() => Math.max(0, matchedCount.value - renamedCount.value))

const hasActive = computed(() =>
  tasks.value.some((task) => task.status === 'running' || task.status === 'pending'),
)
const recentTasks = computed(() => tasks.value.slice(0, 5))

const openlistCount = computed(
  () => store.datasources.filter((source) => source.type === 'openlist').length,
)
const allowedPaths = computed(() => store.settings?.allowed_paths ?? [])
const tmdbReady = computed(() => Boolean(store.settings?.has_tmdb_key))
const jellyfinReady = computed(() =>
  Boolean(store.settings?.jellyfin_url && store.settings?.has_jellyfin_key),
)
const ready = computed(
  () => tmdbReady.value && (allowedPaths.value.length > 0 || openlistCount.value > 0),
)

const sourceLabel = computed(() => (store.sourceType === 'openlist' ? 'OPENLIST' : 'LOCAL'))

const slate = computed<SlateRow[]>(() => [
  { label: 'SOURCE', value: sourceLabel.value },
  { label: 'ROOT', value: store.scanPath || '—' },
  { label: 'LIBRARY', value: `${store.files.length} FILES` },
  {
    label: 'STATE',
    value: ready.value ? 'READY' : 'ATTENTION',
    tone: ready.value ? 'green' : 'amber',
  },
])

const statItems = computed<StatItem[]>(() => [
  { label: 'LIBRARY', value: store.files.length },
  { label: 'VIDEO FILES', value: videoCount.value },
  { label: 'IN QUEUE', value: inQueue.value, tone: inQueue.value ? 'amber' : undefined },
  { label: 'RENAMED', value: renamedCount.value, tone: renamedCount.value ? 'green' : undefined },
])

function ratio(part: number, total: number) {
  return total > 0 ? Math.round((part / total) * 100) : 0
}

const stages = computed<Stage[]>(() => [
  {
    key: 'scan',
    num: '01',
    label: '扫描',
    en: 'INGEST',
    icon: 'scan',
    count: store.files.length,
    sub: store.files.length ? `${videoCount.value} 个视频文件` : '尚未扫描任何目录',
    percent: store.files.length ? 100 : 0,
    route: 'scan',
  },
  {
    key: 'parse',
    num: '02',
    label: '解析',
    en: 'PARSE',
    icon: 'parse',
    count: parsedCount.value,
    sub: pendingParse.value ? `待解析 ${pendingParse.value}` : '全部已解析',
    percent: ratio(parsedCount.value, videoCount.value),
    route: 'parse',
  },
  {
    key: 'scrape',
    num: '03',
    label: '刮削',
    en: 'SCRAPE',
    icon: 'clap',
    count: matchedCount.value,
    sub: pendingScrape.value ? `待匹配 ${pendingScrape.value}` : '全部已匹配',
    percent: ratio(matchedCount.value, parsedCount.value),
    route: 'scrape',
  },
  {
    key: 'rename',
    num: '04',
    label: '重命名',
    en: 'RENAME',
    icon: 'rename',
    count: renamedCount.value,
    sub: pendingRename.value ? `待重命名 ${pendingRename.value}` : '没有待重命名文件',
    percent: ratio(renamedCount.value, matchedCount.value),
    route: 'rename',
  },
])

const checks = computed(() => [
  {
    key: 'tmdb',
    label: 'TMDB 元数据',
    icon: 'sparkles',
    detail: tmdbReady.value ? 'API Key 已配置' : '未配置时将无法搜索与匹配剧集',
    ok: tmdbReady.value,
    state: tmdbReady.value ? 'READY' : 'MISSING',
  },
  {
    key: 'openlist',
    label: 'OpenList 云盘',
    icon: 'cloud',
    detail: openlistCount.value ? `${openlistCount.value} 个实例可用` : '未添加实例，仅能操作本地目录',
    ok: openlistCount.value > 0,
    state: openlistCount.value ? `${openlistCount.value} INST` : 'OPTIONAL',
  },
  {
    key: 'jellyfin',
    label: 'Jellyfin 媒体库',
    icon: 'server',
    detail: jellyfinReady.value
      ? store.settings?.jellyfin_url ?? '已配置'
      : '未配置时将无法一键刷新媒体库',
    ok: jellyfinReady.value,
    state: jellyfinReady.value ? 'READY' : 'MISSING',
  },
  {
    key: 'paths',
    label: '本地白名单',
    icon: 'folder',
    detail: allowedPaths.value.length
      ? `${allowedPaths.value.length} 个根目录`
      : '未配置时将无法扫描本地目录',
    ok: allowedPaths.value.length > 0,
    state: allowedPaths.value.length ? `${allowedPaths.value.length} ROOT` : 'MISSING',
  },
])

function messageOf(err: unknown) {
  return err instanceof Error ? err.message : '请求失败'
}

function shortTime(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function taskPercent(task: Task) {
  if (!task.total) return task.status === 'completed' ? 100 : 0
  return Math.min(100, Math.round(((task.done + task.failed) / task.total) * 100))
}

function typeLabel(type: string) {
  return type === 'rename' ? '重命名' : type
}

function syncPolling() {
  if (timer) {
    window.clearInterval(timer)
    timer = undefined
  }
  if (hasActive.value) {
    timer = window.setInterval(() => void loadTasks(), 12000)
  }
}

async function loadFiles() {
  try {
    await store.refreshFiles()
    error.value = ''
  } catch (err) {
    error.value = messageOf(err)
  }
}

async function loadTasks(reportError = false) {
  syncing.value = true
  try {
    tasks.value = await api.getTasks()
    const active = hasActive.value
    if (hadActive && !active) await store.refreshFiles()
    hadActive = active
    syncPolling()
  } catch (err) {
    if (reportError) error.value = messageOf(err)
  } finally {
    syncing.value = false
  }
}

async function rollback() {
  rollingBack.value = true
  error.value = ''
  try {
    const result = await store.rollback(null)
    rollbackOpen.value = false
    toast.success(
      `已恢复 ${result.restored} 个文件${result.failed > 0 ? `，失败 ${result.failed}` : ''}`,
    )
    await Promise.all([store.refreshFiles(), loadTasks()])
  } catch (err) {
    error.value = messageOf(err)
  } finally {
    rollingBack.value = false
  }
}

function openRoute(name: string) {
  void router.push({ name })
}

onMounted(async () => {
  if (!store.settings) {
    try {
      await store.init()
    } catch (err) {
      error.value = messageOf(err)
    }
  }
  await Promise.all([loadFiles(), loadTasks(true)])
})

onBeforeUnmount(() => {
  if (timer) window.clearInterval(timer)
})
</script>

<template>
  <div>
    <PageHeader
      ghost="00"
      kicker="STAGE 00 · OVERVIEW"
      title="概览"
      title-en="OVERVIEW"
      description="一条从扫描到媒体库刷新的流水线总览：先看各步待办，再决定下一步做什么。"
      :slate="slate"
    >
      <template #actions>
        <button class="btn btn-amber btn-sm" @click="openRoute('scan')">
          <AppIcon name="scan" :size="14" />
          开始扫描
        </button>
        <button class="btn btn-sm" @click="openRoute('parse')">
          <AppIcon name="parse" :size="14" />
          去解析
        </button>
        <button class="btn btn-sm" @click="openRoute('refresh')">
          <AppIcon name="refresh" :size="14" />
          刷新媒体库
        </button>
        <button
          class="btn btn-sm btn-danger"
          :disabled="renamedCount === 0"
          @click="rollbackOpen = true"
        >
          <AppIcon name="undo" :size="14" />
          撤销上次重命名
        </button>
      </template>
    </PageHeader>

    <ErrorBanner v-if="error" class="mb-3.5" title="概览数据加载失败" :message="error" />

    <StatStrip :items="statItems" />

    <section class="panel overview-pipeline">
      <div class="panel-head">
        <div class="panel-title">PIPELINE <b>流水线</b></div>
        <div class="panel-side">
          <span v-if="syncing" class="mono text-[9px] tracking-[0.16em] text-faint">SYNCING…</span>
          <span class="tag" :class="hasActive ? 'tag-warn' : 'tag-mute'">
            {{ hasActive ? 'TASK RUNNING' : 'IDLE' }}
          </span>
        </div>
      </div>

      <div class="pipe-grid">
        <button
          v-for="stage in stages"
          :key="stage.key"
          class="pipe-stage"
          :class="{ empty: stage.count === 0 }"
          @click="openRoute(stage.route)"
        >
          <span class="pipe-top">
            <span class="pipe-num">{{ stage.num }}</span>
            <AppIcon :name="stage.icon" :size="14" class="pipe-ic" />
          </span>
          <span class="pipe-label">
            {{ stage.label }}
            <small>{{ stage.en }}</small>
          </span>
          <b class="pipe-count">
            {{ stage.count }}
            <em v-if="stage.percent">/ {{ stage.percent }}%</em>
          </b>
          <span class="pipe-sub">{{ stage.sub }}</span>
          <span class="pipe-bar" aria-hidden="true">
            <i :style="{ width: `${stage.percent}%` }" />
          </span>
        </button>
      </div>

      <div class="pipe-foot">
        <span class="dot" :class="ready ? 'ok' : 'warn'" />
        <span>SOURCE <b>{{ sourceLabel }}</b></span>
        <span class="sep">/</span>
        <span class="pipe-root">
          ROOT <b>{{ store.scanPath || '未选择目录' }}</b>
        </span>
        <span class="grow" />
        <span>LIBRARY <b>{{ store.files.length }}</b></span>
        <span class="sep">/</span>
        <span>IN QUEUE <b>{{ inQueue }}</b></span>
        <button class="pipe-link" @click="openRoute('refresh')">
          收尾 · 刷新媒体库
          <AppIcon name="arrow-right" :size="12" />
        </button>
      </div>
    </section>

    <div class="overview-grid">
      <section class="panel">
        <div class="panel-head">
          <div class="panel-title">RECENT TASKS <b>最近任务</b></div>
          <div class="panel-side">
            <button class="btn btn-xs btn-ghost" @click="openRoute('tasks')">全部任务</button>
          </div>
        </div>

        <div v-if="recentTasks.length" class="task-list">
          <button
            v-for="task in recentTasks"
            :key="task.id"
            class="task-row"
            @click="openRoute('tasks')"
          >
            <span class="task-main">
              <span class="task-line">
                <StatusTag :status="task.status" />
                <b class="task-type">{{ typeLabel(task.type) }}</b>
                <span class="task-id">{{ task.id.slice(0, 8) }}</span>
                <span class="task-time">{{ shortTime(task.created_at) }}</span>
              </span>
              <span class="task-meta">
                <span>成功 {{ task.done }}</span>
                <span :class="{ red: task.failed > 0 }">失败 {{ task.failed }}</span>
                <span>共 {{ task.total }}</span>
                <span v-if="task.error" class="task-error">{{ task.error }}</span>
              </span>
              <span class="task-bar" aria-hidden="true">
                <i
                  :class="{ danger: task.failed > 0, green: task.status === 'completed' && !task.failed }"
                  :style="{ width: `${taskPercent(task)}%` }"
                />
              </span>
            </span>
            <span class="task-pct">
              {{ taskPercent(task) }}<small>%</small>
            </span>
          </button>
        </div>

        <EmptyState
          v-else
          icon="tasks"
          title="还没有后台任务"
          description="重命名任务提交后会出现在这里，运行状态与逐项进度会自动刷新。"
        >
          <button class="btn btn-sm" @click="openRoute('rename')">去重命名</button>
        </EmptyState>
      </section>

      <section class="panel">
        <div class="panel-head">
          <div class="panel-title">SYSTEM CHECK <b>系统就绪度</b></div>
          <div class="panel-side">
            <button class="btn btn-xs btn-ghost" @click="openRoute('settings')">打开设置</button>
          </div>
        </div>

        <div class="check-list">
          <button
            v-for="check in checks"
            :key="check.key"
            class="check-row"
            @click="openRoute('settings')"
          >
            <span class="check-ic">
              <AppIcon :name="check.icon" :size="15" />
            </span>
            <span class="check-copy">
              <b>{{ check.label }}</b>
              <small>{{ check.detail }}</small>
            </span>
            <span class="check-state" :class="check.ok ? 'ok' : 'warn'">
              <span class="dot" :class="check.ok ? 'ok' : 'warn'" />
              {{ check.state }}
            </span>
          </button>
        </div>

        <div class="check-foot">
          当前数据源
          <b>{{ sourceLabel }}</b>
          <span class="sep">/</span>
          <span class="check-root">{{ store.scanPath || '未选择扫描根' }}</span>
        </div>
      </section>
    </div>

    <ConfirmDialog
      :open="rollbackOpen"
      title="撤销上次重命名"
      message="将把最近一次重命名任务中的文件恢复为原名。已写入的 NFO、海报与 STRM 不会被删除。"
      confirm-text="撤销"
      danger
      :loading="rollingBack"
      @confirm="rollback"
      @cancel="rollbackOpen = false"
    />
  </div>
</template>
