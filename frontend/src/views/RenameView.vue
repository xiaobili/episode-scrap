<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import { wsUrl } from '@/api/client'
import AppIcon from '@/components/AppIcon.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import DiffText from '@/components/DiffText.vue'
import EmptyState from '@/components/EmptyState.vue'
import ErrorBanner from '@/components/ErrorBanner.vue'
import StatusTag from '@/components/StatusTag.vue'
import TaskProgress from '@/components/TaskProgress.vue'
import TemplateEditor from '@/components/TemplateEditor.vue'
import { useToast } from '@/composables/useToast'
import { useWorkflowStore } from '@/stores/workflow'

const store = useWorkflowStore()
const router = useRouter()
const toast = useToast()

const template = ref('')
const writeNfo = ref(true)
const posters = ref(true)
const policy = ref<'skip' | 'suffix'>('skip')
const includeIds = ref<number[]>([])
const confirmOpen = ref(false)
const rollbackOpen = ref(false)
const rollingBack = ref(false)
const error = ref('')

interface LiveTask {
  id: string
  total: number
  done: number
  failed: number
  status: string
}

const activeTask = ref<LiveTask | null>(null)
let socket: WebSocket | null = null

const sample = computed(() => store.parsedFiles[0] ?? null)
const preview = computed(() => store.preview)
const items = computed(() => preview.value?.items ?? [])
const readyItems = computed(() => items.value.filter((item) => item.status === 'ready'))
const chosenItems = computed(() =>
  readyItems.value.filter((item) => includeIds.value.includes(item.file_id)),
)

watch(
  () => store.settings?.rename_template,
  (value) => {
    if (value && !template.value) template.value = value
  },
  { immediate: true },
)

watch(
  preview,
  (value) => {
    if (value) {
      includeIds.value = value.items
        .filter((item) => item.status === 'ready')
        .map((item) => item.file_id)
    }
  },
  { immediate: true },
)

function messageOf(err: unknown) {
  return err instanceof Error ? err.message : '请求失败'
}

function targetIds(): number[] | undefined {
  const ids = store.selectedFiles.filter((file) => file.is_video).map((file) => file.id)
  return ids.length > 0 ? ids : undefined
}

async function runPreview() {
  if (!template.value.trim()) {
    error.value = '命名模板不能为空'
    return
  }
  error.value = ''
  try {
    await store.previewRename(targetIds(), template.value)
  } catch (err) {
    error.value = messageOf(err)
  }
}

function toggleInclude(fileId: number) {
  includeIds.value = includeIds.value.includes(fileId)
    ? includeIds.value.filter((id) => id !== fileId)
    : [...includeIds.value, fileId]
}

function toggleAllReady() {
  includeIds.value =
    chosenItems.value.length === readyItems.value.length
      ? []
      : readyItems.value.map((item) => item.file_id)
}

async function execute() {
  if (chosenItems.value.length === 0) {
    error.value = '没有可执行的项目'
    confirmOpen.value = false
    return
  }
  error.value = ''
  try {
    const result = await store.executeRename(
      chosenItems.value.map((item) => item.file_id),
      {
        template: template.value,
        write_nfo: writeNfo.value,
        download_posters: posters.value,
        conflict_policy: policy.value,
      },
    )
    confirmOpen.value = false
    activeTask.value = {
      id: result.task_id,
      total: result.total,
      done: 0,
      failed: 0,
      status: 'running',
    }
    connect(result.task_id)
    toast.success(`已创建任务，共 ${result.total} 项`)
  } catch (err) {
    error.value = messageOf(err)
    confirmOpen.value = false
  }
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
    }
    if (!activeTask.value || activeTask.value.id !== taskId) return
    activeTask.value = {
      ...activeTask.value,
      status: data.status,
      total: data.total,
      done: data.done,
      failed: data.failed,
    }
    if (data.status === 'completed') {
      disconnect()
      void store.refreshFiles()
      toast.success(`重命名完成：成功 ${data.done}，失败 ${data.failed}`)
    }
  }
  ws.onerror = () => disconnect()
}

function disconnect() {
  socket?.close()
  socket = null
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
    activeTask.value = null
    store.resetDownstream()
    await store.refreshFiles()
  } catch (err) {
    error.value = messageOf(err)
  } finally {
    rollingBack.value = false
  }
}

onMounted(() => {
  if (!template.value && store.settings) template.value = store.settings.rename_template
})
onBeforeUnmount(disconnect)
</script>

<template>
  <div>
    <header class="mb-5 flex flex-wrap items-start gap-3">
      <div class="min-w-0 flex-1">
        <h1 class="text-2xl font-semibold leading-8 tracking-tight text-ink">重命名</h1>
        <p class="mt-1 text-[13px] text-muted">配置命名模板，预览差异后执行，可随时撤销</p>
      </div>
      <button class="btn btn-danger" :disabled="rollingBack" @click="rollbackOpen = true">
        <AppIcon name="undo" :size="14" />
        撤销上次
      </button>
    </header>

    <ErrorBanner v-if="error" class="mb-4" :message="error" />

    <div v-if="store.parsedFiles.length === 0" class="panel">
      <EmptyState
        icon="rename"
        title="没有可重命名的文件"
        description="请先完成扫描与解析，再回来生成命名方案。"
      >
        <button class="btn btn-primary" @click="router.push('/parse')">
          <AppIcon name="parse" :size="14" />
          去解析
        </button>
      </EmptyState>
    </div>

    <template v-else>
      <section class="panel p-4">
        <div class="mb-2 flex items-center justify-between">
          <span class="text-[13px] font-medium text-ink">命名模板</span>
          <span class="text-[11px] text-faint">目标文件将保留原扩展名</span>
        </div>
        <TemplateEditor v-model="template" :sample="sample" />
        <p class="mt-2 text-[11.5px] text-faint">
          可用变量：{title} {year} {season} {episode} {episode_title} {resolution} {codec} {release_group}，数字可用 :02d 补零。
        </p>
      </section>

      <section class="mt-4 panel overflow-hidden">
        <div class="flex flex-wrap items-center gap-2 border-b border-line px-4 py-3">
          <button class="btn" :disabled="store.previewing" @click="runPreview">
            <AppIcon name="refresh" :size="14" :spin="store.previewing" />
            仅预览
          </button>

          <span v-if="preview" class="flex items-center gap-1.5 text-[11.5px]">
            <span class="tag tag-success">可执行 {{ preview.ready }}</span>
            <span v-if="preview.conflicts" class="tag tag-warning">冲突 {{ preview.conflicts }}</span>
            <span v-if="preview.skipped" class="tag">跳过 {{ preview.skipped }}</span>
          </span>

          <div class="ml-auto flex flex-wrap items-center gap-3">
            <label class="flex cursor-pointer select-none items-center gap-1.5 text-xs text-muted">
              <input v-model="writeNfo" type="checkbox" class="h-3.5 w-3.5 accent-accent" />
              同时写入 NFO
            </label>
            <label class="flex cursor-pointer select-none items-center gap-1.5 text-xs text-muted">
              <input v-model="posters" type="checkbox" class="h-3.5 w-3.5 accent-accent" />
              下载海报
            </label>
            <label class="flex items-center gap-1.5 text-xs text-muted">
              冲突处理
              <select v-model="policy" class="select h-7 !w-auto text-xs">
                <option value="skip">跳过同名</option>
                <option value="suffix">自动加后缀</option>
              </select>
            </label>
            <button
              class="btn btn-primary"
              :disabled="store.executing || chosenItems.length === 0"
              @click="confirmOpen = true"
            >
              <AppIcon name="rename" :size="14" />
              执行重命名（{{ chosenItems.length }}）
            </button>
          </div>
        </div>

        <div v-if="activeTask" class="border-b border-line px-4 py-3">
          <div class="mb-2 flex items-center gap-2">
            <StatusTag :status="activeTask.status" />
            <span class="font-mono text-xs text-muted">{{ activeTask.id.slice(0, 8) }}</span>
            <router-link
              to="/tasks"
              class="ml-auto text-[11.5px] text-accent hover:underline"
            >
              查看任务
            </router-link>
          </div>
          <TaskProgress
            :total="activeTask.total"
            :done="activeTask.done"
            :failed="activeTask.failed"
            :status="activeTask.status"
          />
        </div>

        <div v-if="!preview" class="px-4">
          <EmptyState
            icon="rename"
            :title="store.selectedFiles.length ? `已选 ${store.selectedFiles.length} 项` : '尚未生成预览'"
            description="点击「仅预览」查看重命名结果，预览不会修改任何文件。"
          />
        </div>

        <div v-else-if="items.length === 0" class="px-4">
          <EmptyState icon="filter" title="没有可处理的项目" description="检查当前选择与解析结果后重试。" />
        </div>

        <div v-else class="overflow-x-auto">
          <table class="w-full min-w-[760px] border-collapse text-[13px]">
            <thead>
              <tr class="border-b border-line text-left text-xs text-faint">
                <th class="h-10 w-10 pl-4">
                  <input
                    type="checkbox"
                    class="h-4 w-4 accent-accent"
                    :checked="readyItems.length > 0 && chosenItems.length === readyItems.length"
                    aria-label="全选可执行项"
                    @change="toggleAllReady"
                  />
                </th>
                <th class="h-10 px-3 font-medium">原文件名</th>
                <th class="h-10 px-3 font-medium">新文件名</th>
                <th class="h-10 w-24 px-3 font-medium">状态</th>
                <th class="h-10 w-44 px-3 font-medium">说明</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="item in items"
                :key="item.file_id"
                class="h-11 border-b border-line/60 last:border-0"
                :class="item.status === 'conflict' ? 'bg-[rgba(245,184,73,.07)]' : ''"
              >
                <td class="pl-4">
                  <input
                    type="checkbox"
                    class="h-4 w-4 accent-accent"
                    :checked="includeIds.includes(item.file_id)"
                    :disabled="item.status !== 'ready'"
                    :aria-label="`选择 ${item.original_name}`"
                    @change="toggleInclude(item.file_id)"
                  />
                </td>
                <td class="max-w-0 px-3">
                  <span class="block truncate font-mono text-xs text-muted" :title="item.original_name">
                    {{ item.original_name }}
                  </span>
                </td>
                <td class="max-w-0 px-3">
                  <DiffText :before="item.original_name" :after="item.new_name ?? '—'" />
                </td>
                <td class="px-3"><StatusTag :status="item.status" /></td>
                <td class="px-3">
                  <span class="block truncate text-[11.5px] text-faint" :title="item.reason ?? ''">
                    {{ item.reason ?? '—' }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <div class="mt-4 flex items-center justify-between gap-2">
        <button class="btn btn-ghost" @click="router.push('/scrape')">
          <AppIcon name="arrow-left" :size="14" />
          上一步
        </button>
        <span class="text-[11.5px] text-faint">
          执行前会再次确认影响范围，执行后可在任务中心查看进度
        </span>
      </div>
    </template>

    <ConfirmDialog
      :open="confirmOpen"
      title="执行重命名"
      :message="`将处理 ${chosenItems.length} 个文件${writeNfo ? '，并写入 NFO' : ''}。\n执行后可随时在重命名页或任务中心撤销。`"
      confirm-text="确认执行"
      :loading="store.executing"
      @confirm="execute"
      @cancel="confirmOpen = false"
    />

    <ConfirmDialog
      :open="rollbackOpen"
      title="撤销上次重命名"
      message="将把最近一次重命名任务中的文件恢复为原文件名，已写入的 NFO 不会自动删除。"
      confirm-text="确认撤销"
      danger
      :loading="rollingBack"
      @confirm="rollback"
      @cancel="rollbackOpen = false"
    />
  </div>
</template>
