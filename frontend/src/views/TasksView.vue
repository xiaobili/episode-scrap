<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import { api, wsUrl } from '@/api/client'
import AppIcon from '@/components/AppIcon.vue'
import BaseDrawer from '@/components/BaseDrawer.vue'
import EmptyState from '@/components/EmptyState.vue'
import ErrorBanner from '@/components/ErrorBanner.vue'
import StatusTag from '@/components/StatusTag.vue'
import TaskProgress from '@/components/TaskProgress.vue'
import { useToast } from '@/composables/useToast'
import type { Task, TaskDetail } from '@/types'

const toast = useToast()

const tasks = ref<Task[]>([])
const filter = ref('')
const loading = ref(false)
const error = ref('')
const detail = ref<TaskDetail | null>(null)
const drawerOpen = ref(false)
const retrying = ref(false)

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
  }
}

async function open(task: Task) {
  drawerOpen.value = true
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
  drawerOpen.value = false
  disconnect()
}

function connect(taskId: string) {
  disconnect()
  const ws = new WebSocket(wsUrl(taskId))
  socket = ws
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data) as {
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
}

function disconnect() {
  socket?.close()
  socket = null
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
  return type
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
    <header class="mb-5 flex flex-wrap items-start gap-3">
      <div class="min-w-0 flex-1">
        <h1 class="text-2xl font-semibold leading-8 tracking-tight text-ink">任务中心</h1>
        <p class="mt-1 text-[13px] text-muted">查看历史任务与逐项执行结果，失败项可重试</p>
      </div>
      <div class="flex items-center gap-2">
        <select v-model="filter" class="select !w-auto text-xs">
          <option v-for="item in filters" :key="item.value" :value="item.value">
            {{ item.label }}
          </option>
        </select>
        <button class="btn" :disabled="loading" @click="load">
          <AppIcon name="refresh" :size="14" :spin="loading" />
          刷新
        </button>
      </div>
    </header>

    <ErrorBanner v-if="error" class="mb-4" :message="error" retryable @retry="load" />

    <section class="panel overflow-hidden">
      <div v-if="loading && tasks.length === 0" class="divide-y divide-line/60">
        <div v-for="index in 5" :key="index" class="flex h-12 items-center gap-6 px-4">
          <span class="h-3 w-16 animate-pulse rounded bg-[var(--bg-elevated)]" />
          <span class="h-3 flex-1 animate-pulse rounded bg-[var(--bg-elevated)]" />
          <span class="h-3 w-28 animate-pulse rounded bg-[var(--bg-elevated)]" />
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
        <table class="w-full min-w-[820px] border-collapse text-[13px]">
          <thead>
            <tr class="border-b border-line text-left text-xs text-faint">
              <th class="h-10 px-4 font-medium">类型</th>
              <th class="h-10 w-24 px-3 font-medium">数据源</th>
              <th class="h-10 w-52 px-3 font-medium">进度</th>
              <th class="h-10 w-24 px-3 font-medium">成功 / 失败</th>
              <th class="h-10 w-24 px-3 font-medium">状态</th>
              <th class="h-10 w-32 px-3 font-medium">开始时间</th>
              <th class="h-10 w-20 px-4 font-medium" />
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="task in tasks"
              :key="task.id"
              class="h-12 cursor-pointer border-b border-line/60 transition-colors last:border-0 hover:bg-[var(--bg-elevated)]"
              @click="open(task)"
            >
              <td class="px-4">
                <span class="font-medium text-ink">{{ typeLabel(task.type) }}</span>
                <span class="ml-2 font-mono text-[11px] text-faint">{{ task.id.slice(0, 8) }}</span>
              </td>
              <td class="px-3">
                <span class="tag" :class="task.source_type === 'openlist' ? 'tag-info' : ''">
                  {{ task.source_type === 'openlist' ? 'OpenList' : '本地' }}
                </span>
              </td>
              <td class="px-3">
                <TaskProgress
                  :total="task.total"
                  :done="task.done"
                  :failed="task.failed"
                  :status="task.status"
                />
              </td>
              <td class="px-3 font-mono text-xs">
                <span class="text-success">{{ task.done }}</span>
                <span class="mx-1 text-faint">/</span>
                <span :class="task.failed ? 'text-danger' : 'text-faint'">{{ task.failed }}</span>
              </td>
              <td class="px-3"><StatusTag :status="task.status" /></td>
              <td class="px-3 font-mono text-xs text-faint">{{ formatTime(task.created_at) }}</td>
              <td class="px-4 text-right">
                <span class="text-[11.5px] text-accent">详情</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <BaseDrawer :open="drawerOpen" title="任务详情" :width="520" @close="close">
      <div v-if="!detail" class="space-y-2">
        <div v-for="index in 4" :key="index" class="h-10 animate-pulse rounded bg-[var(--bg-elevated)]" />
      </div>

      <template v-else>
        <div class="flex items-center gap-2">
          <StatusTag :status="detail.status" />
          <span class="font-mono text-xs text-muted">{{ detail.id }}</span>
        </div>

        <div class="mt-3">
          <TaskProgress
            :total="detail.total"
            :done="detail.done"
            :failed="detail.failed"
            :status="detail.status"
          />
        </div>

        <dl class="mt-4 grid grid-cols-2 gap-x-4 gap-y-2 text-xs">
          <div>
            <dt class="text-faint">类型</dt>
            <dd class="mt-0.5 text-ink">{{ typeLabel(detail.type) }}</dd>
          </div>
          <div>
            <dt class="text-faint">数据源</dt>
            <dd class="mt-0.5 text-ink">
              {{ detail.source_type === 'openlist' ? 'OpenList' : '本地' }}
            </dd>
          </div>
          <div>
            <dt class="text-faint">开始时间</dt>
            <dd class="mt-0.5 font-mono text-ink">{{ formatTime(detail.created_at) }}</dd>
          </div>
          <div>
            <dt class="text-faint">结束时间</dt>
            <dd class="mt-0.5 font-mono text-ink">{{ formatTime(detail.finished_at) }}</dd>
          </div>
          <div class="col-span-2">
            <dt class="text-faint">命名模板</dt>
            <dd class="mt-0.5 break-all font-mono text-[11.5px] text-muted">
              {{ detail.template ?? '—' }}
            </dd>
          </div>
        </dl>

        <div class="my-3 divider" />

        <div class="mb-2 flex items-center justify-between">
          <span class="text-xs font-medium text-muted">逐项结果</span>
          <span class="font-mono text-[11px] text-faint">{{ detail.items.length }} 项</span>
        </div>

        <div v-if="detail.items.length === 0" class="py-8 text-center text-xs text-faint">
          暂无明细
        </div>

        <div v-else class="divide-y divide-line/60 rounded-md border border-line">
          <div
            v-for="item in detail.items"
            :key="item.id"
            class="flex items-start gap-2 px-2.5 py-2"
          >
            <StatusTag :status="item.status" class="mt-0.5 flex-none" />
            <div class="min-w-0 flex-1">
              <p class="truncate font-mono text-[11.5px] text-muted" :title="item.name">
                {{ item.name }}
              </p>
              <p v-if="item.new_name" class="truncate font-mono text-[11.5px] text-ink" :title="item.new_name">
                → {{ item.new_name }}
              </p>
              <p v-if="item.error" class="mt-0.5 break-words text-[11px] text-danger">
                {{ item.error }}
              </p>
            </div>
          </div>
        </div>

        <div v-if="detail.error" class="mt-3">
          <ErrorBanner title="任务错误" :message="detail.error" />
        </div>
      </template>

      <template v-if="detail" #footer>
        <button class="btn btn-ghost" @click="close">关闭</button>
        <button
          class="btn btn-primary"
          :disabled="retrying || detail.failed === 0"
          @click="retry"
        >
          <AppIcon name="refresh" :size="14" :spin="retrying" />
          重试失败项
        </button>
      </template>
    </BaseDrawer>
  </div>
</template>
