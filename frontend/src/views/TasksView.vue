<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import { api, wsUrl } from '@/api/client'
import AppIcon from '@/components/AppIcon.vue'
import EmptyState from '@/components/EmptyState.vue'
import ErrorBanner from '@/components/ErrorBanner.vue'
import PageHeader from '@/components/PageHeader.vue'
import SegmentedControl from '@/components/SegmentedControl.vue'
import StatusTag from '@/components/StatusTag.vue'
import TaskProgress from '@/components/TaskProgress.vue'
import type { SlateRow } from '@/components/ui-types'
import { useToast } from '@/composables/useToast'
import type { Task, TaskDetail } from '@/types'

const toast = useToast()

const tasks = ref<Task[]>([])
const filter = ref('')
const loading = ref(false)
const error = ref('')
const detail = ref<TaskDetail | null>(null)
const retrying = ref(false)
const socketConnected = ref(false)
const lastSync = ref('')

let socket: WebSocket | null = null
let timer: number | undefined

const filters = [
  { value: '', label: '全部' },
  { value: 'running', label: '运行中' },
  { value: 'pending', label: '等待中' },
  { value: 'completed', label: '已完成' },
]

const hasActive = computed(() =>
  tasks.value.some((task) => task.status === 'running' || task.status === 'pending'),
)

const runningCount = computed(() => tasks.value.filter((task) => task.status === 'running').length)
const queuedCount = computed(() => tasks.value.filter((task) => task.status === 'pending').length)
const doneToday = computed(
  () =>
    tasks.value.filter((task) => task.status === 'completed' && isToday(task.created_at)).length,
)

const slate = computed<SlateRow[]>(() => [
  { label: 'RUNNING', value: String(runningCount.value), tone: runningCount.value ? 'amber' : undefined },
  { label: 'QUEUED', value: String(queuedCount.value) },
  { label: 'DONE TODAY', value: String(doneToday.value) },
  {
    label: 'SOCKET',
    value: socketConnected.value ? 'CONNECTED' : 'IDLE',
    tone: socketConnected.value ? 'green' : undefined,
  },
])

const detailPercent = computed(() => {
  if (!detail.value) return 0
  if (!detail.value.total) return detail.value.status === 'completed' ? 100 : 0
  return Math.min(
    100,
    Math.round(((detail.value.done + detail.value.failed) / detail.value.total) * 100),
  )
})

function isToday(value: string) {
  const date = new Date(value)
  return !Number.isNaN(date.getTime()) && date.toDateString() === new Date().toDateString()
}

function messageOf(err: unknown) {
  return err instanceof Error ? err.message : '请求失败'
}

async function load() {
  loading.value = true
  try {
    tasks.value = await api.getTasks(filter.value ? { status: filter.value } : undefined)
    error.value = ''
  } catch (err) {
    error.value = messageOf(err)
  } finally {
    loading.value = false
    lastSync.value = new Date().toLocaleTimeString()
  }
}

async function open(task: Task) {
  disconnect()
  detail.value = null
  error.value = ''
  try {
    detail.value = await api.getTask(task.id)
    connect(task.id)
  } catch (err) {
    error.value = messageOf(err)
  }
}

function close() {
  detail.value = null
  disconnect()
}

function connect(taskId: string) {
  disconnect()
  const ws = new WebSocket(wsUrl(taskId))
  socket = ws
  ws.onopen = () => {
    socketConnected.value = true
  }
  ws.onmessage = (event) => {
    let data: {
      status: string
      total: number
      done: number
      failed: number
      item?: {
        id: number
        name: string
        new_name: string | null
        status: string
        error: string | null
      }
    }
    try {
      data = JSON.parse(event.data) as typeof data
    } catch {
      return
    }
    if (!detail.value || detail.value.id !== taskId) return

    detail.value = {
      ...detail.value,
      status: data.status,
      total: data.total,
      done: data.done,
      failed: data.failed,
    }
    if (data.item) {
      const index = detail.value.items.findIndex((item) => item.id === data.item?.id)
      if (index >= 0) detail.value.items[index] = { ...detail.value.items[index], ...data.item }
      else detail.value.items.push({ ...data.item, file_id: null })
    }
    if (data.status === 'completed') {
      disconnect()
      void load()
    }
  }
  ws.onerror = () => disconnect()
  ws.onclose = () => {
    socketConnected.value = false
  }
}

function disconnect() {
  socket?.close()
  socket = null
  socketConnected.value = false
}

async function retry() {
  if (!detail.value) return
  retrying.value = true
  error.value = ''
  try {
    await api.retryTask(detail.value.id)
    toast.success('已重新提交失败项')
    close()
    await load()
  } catch (err) {
    error.value = messageOf(err)
  } finally {
    retrying.value = false
  }
}

async function copyId() {
  if (!detail.value) return
  try {
    await navigator.clipboard.writeText(detail.value.id)
    toast.info('任务 ID 已复制')
  } catch {
    toast.error('复制失败')
  }
}

function formatTime(value: string | null) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  const pad = (num: number) => String(num).padStart(2, '0')
  return `${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
}

function typeLabel(type: string) {
  if (type === 'rename') return '重命名'
  if (type === 'scrape') return '刮削'
  if (type === 'refresh') return '媒体库刷新'
  return type
}

function typeIcon(type: string) {
  if (type === 'rename') return 'rename'
  if (type === 'scrape') return 'sparkles'
  if (type === 'refresh') return 'refresh'
  return 'tasks'
}

function itemDot(status: string) {
  if (status === 'success' || status === 'ready' || status === 'renamed') return 'ok'
  if (status === 'failed' || status === 'error') return 'bad'
  return 'warn'
}

function setFilter(value: string | number) {
  filter.value = String(value)
}

watch(filter, load)

onMounted(() => {
  void load()
  timer = window.setInterval(() => {
    if (hasActive.value) void load()
  }, 5000)
})

onBeforeUnmount(() => {
  disconnect()
  if (timer) window.clearInterval(timer)
})
</script>

<template>
  <div>
    <PageHeader
      ghost="05"
      kicker="OPERATIONS · TASKS"
      title="任务中心"
      title-en="TASKS"
      description="后台任务实时进度、逐项结果与失败重试。任务在离开页面后继续运行。"
      :slate="slate"
    />

    <ErrorBanner v-if="error" class="mb-4" :message="error" retryable @retry="load" />

    <div class="tasks-grid">
      <section class="panel">
        <div class="table-toolbar">
          <div class="toolbar-title">
            <span>TASK LOG</span>
            <b>{{ tasks.length }} RECORDS</b>
          </div>
          <div class="toolbar-right">
            <SegmentedControl
              :model-value="filter"
              :options="filters"
              size="sm"
              aria-label="任务状态筛选"
              @update:model-value="setFilter"
            />
            <button class="icon-btn" :disabled="loading" title="刷新" @click="load">
              <AppIcon name="refresh" :size="14" :spin="loading" />
            </button>
          </div>
        </div>

        <div v-if="loading && tasks.length === 0" class="divide-y divide-line/60">
          <div v-for="index in 5" :key="index" class="flex h-12 items-center gap-6 px-4">
            <span class="h-3 w-16 animate-pulse rounded bg-[var(--surface-2)]" />
            <span class="h-3 flex-1 animate-pulse rounded bg-[var(--surface-2)]" />
            <span class="h-3 w-28 animate-pulse rounded bg-[var(--surface-2)]" />
          </div>
        </div>

        <div v-else-if="tasks.length === 0" class="px-4">
          <EmptyState
            icon="tasks"
            title="暂无任务"
            description="执行重命名后会在这里生成任务记录，运行中的任务将实时更新进度。"
          />
        </div>

        <div v-else class="overflow-x-auto">
          <table class="min-w-[720px]">
            <thead>
              <tr>
                <th>任务 / 类型</th>
                <th class="w-24">数据源</th>
                <th class="w-52">进度</th>
                <th class="w-24">状态</th>
                <th class="th-date w-32">开始</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="task in tasks"
                :key="task.id"
                class="task-row"
                :class="{ on: detail?.id === task.id }"
                tabindex="0"
                @click="open(task)"
                @keydown.enter="open(task)"
              >
                <td>
                  <div class="task-type">
                    <span class="ic"><AppIcon :name="typeIcon(task.type)" :size="14" /></span>
                    <span>
                      <b>{{ typeLabel(task.type) }}</b>
                      <small>{{ task.id.slice(0, 8) }}</small>
                    </span>
                  </div>
                </td>
                <td>
                  <span class="tag" :class="task.source_type === 'openlist' ? 'tag-info' : 'tag-amber'">
                    {{ task.source_type === 'openlist' ? 'OPENLIST' : 'LOCAL' }}
                  </span>
                </td>
                <td class="progress-cell">
                  <TaskProgress
                    :total="task.total"
                    :done="task.done"
                    :failed="task.failed"
                    :status="task.status"
                  />
                </td>
                <td><StatusTag :status="task.status" /></td>
                <td class="cell-date th-date">{{ formatTime(task.created_at) }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="table-foot">
          <span>REALTIME VIA WS · /ws/tasks/{id}</span>
          <span>LAST SYNC {{ lastSync || '—' }}</span>
        </div>
      </section>

      <section class="panel">
        <div class="panel-head">
          <span class="panel-title">DETAIL <b>任务详情</b></span>
          <button v-if="detail" class="icon-btn" title="关闭详情" @click="close">
            <AppIcon name="x" :size="13" />
          </button>
        </div>

        <div v-if="!detail">
          <EmptyState
            icon="tasks"
            title="选择左侧任务"
            description="选中任务后查看实时进度、逐项结果与失败重试。"
          />
        </div>

        <template v-else>
          <div class="detail-head">
            <div class="id">TASK / {{ detail.id }}</div>
            <h3>{{ typeLabel(detail.type) }}</h3>
            <div class="sub">
              {{ detail.source_type === 'openlist' ? 'OPENLIST' : 'LOCAL' }} · 启动于
              {{ formatTime(detail.created_at) }}
            </div>
          </div>

          <div class="detail-progress">
            <div class="big">
              <b>{{ detailPercent }}%</b>
              <span>{{ detail.done }} DONE / {{ detail.failed }} FAILED / {{ detail.total }} TOTAL</span>
            </div>
            <div class="bar" :class="{ green: detail.status === 'completed' && !detail.failed }">
              <i :style="{ width: `${detailPercent}%` }" />
            </div>
          </div>

          <div class="detail-meta">
            <div>
              <div class="k">TEMPLATE</div>
              <div class="v mono" :title="detail.template ?? ''">{{ detail.template ?? '—' }}</div>
            </div>
            <div>
              <div class="k">STATUS</div>
              <div class="v"><StatusTag :status="detail.status" /></div>
            </div>
            <div>
              <div class="k">FINISHED</div>
              <div class="v mono">{{ formatTime(detail.finished_at) }}</div>
            </div>
            <div>
              <div class="k">NFO</div>
              <div class="v">{{ detail.write_nfo ? '开启 · episodedetails' : '关闭' }}</div>
            </div>
          </div>

          <div class="task-items">
            <div v-if="detail.items.length === 0" class="py-8 text-center text-xs text-faint">
              暂无明细
            </div>
            <template v-else>
              <div v-for="item in detail.items" :key="item.id" class="task-item">
                <span class="dot" :class="itemDot(item.status)" />
                <span class="nm">
                  {{ item.name }}
                  <small v-if="item.new_name">→ {{ item.new_name }}</small>
                  <small v-if="item.error" class="text-danger">{{ item.error }}</small>
                </span>
                <StatusTag :status="item.status" />
              </div>
            </template>
          </div>

          <div v-if="detail.error" class="px-4 py-3">
            <ErrorBanner title="任务错误" :message="detail.error" />
          </div>

          <div class="detail-foot">
            <button class="btn btn-sm btn-ghost" @click="copyId">复制 ID</button>
            <button
              class="btn btn-sm ml-auto"
              :disabled="retrying || detail.failed === 0"
              @click="retry"
            >
              <AppIcon name="refresh" :size="13" :spin="retrying" />
              重试失败项
            </button>
          </div>
        </template>
      </section>
    </div>
  </div>
</template>
