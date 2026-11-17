<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { api } from '@/api/client'
import AppIcon from '@/components/AppIcon.vue'
import { useTimecode } from '@/composables/useClock'
import { useToast } from '@/composables/useToast'
import { useWorkflowStore } from '@/stores/workflow'

const store = useWorkflowStore()
const route = useRoute()
const router = useRouter()
const toast = useToast()

const timecode = useTimecode(24)
const version = __APP_VERSION__
const runningTasks = ref(0)

const steps = computed(() => [
  {
    name: 'scan',
    label: '扫描',
    en: 'INGEST',
    icon: 'scan',
    num: '01',
    count: store.stepCounts.scan,
    disabled: false,
  },
  {
    name: 'parse',
    label: '解析',
    en: 'PARSE',
    icon: 'parse',
    num: '02',
    count: store.stepCounts.parse,
    disabled: store.stepCounts.scan === 0,
  },
  {
    name: 'scrape',
    label: '刮削',
    en: 'SCRAPE',
    icon: 'clap',
    num: '03',
    count: store.stepCounts.scrape,
    disabled: store.stepCounts.parse === 0,
  },
  {
    name: 'rename',
    label: '重命名',
    en: 'RENAME',
    icon: 'rename',
    num: '04',
    count: store.stepCounts.rename,
    disabled: store.stepCounts.parse === 0,
  },
])

const sourceLabel = computed(() => (store.sourceType === 'openlist' ? 'OPENLIST' : 'LOCAL'))
const sourceValue = computed(() => store.scanPath || '—')
const inQueue = computed(
  () =>
    store.parsedFiles.filter((file) => file.status !== 'matched' && file.status !== 'renamed').length,
)
const highlights = computed(() => {
  const done = steps.value.filter((step) => step.count > 0).length
  return Math.round((done / steps.value.length) * 12)
})

function navigate(name: string, disabled = false) {
  if (disabled) return
  if (route.name !== name) router.push({ name })
}

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') store.clearSelection()
}

async function loadTaskBadge() {
  try {
    const tasks = await api.getTasks()
    runningTasks.value = tasks.filter(
      (task) => task.status === 'running' || task.status === 'pending',
    ).length
  } catch {
    runningTasks.value = 0
  }
}

watch(
  () => route.name,
  () => {
    if (route.name === 'tasks') void loadTaskBadge()
  },
)

onMounted(async () => {
  document.addEventListener('keydown', onKeydown)
  await loadTaskBadge()
  try {
    await store.init()
  } catch (error) {
    toast.error(error instanceof Error ? error.message : '初始化失败')
  }
})

onBeforeUnmount(() => document.removeEventListener('keydown', onKeydown))
</script>

<template>
  <div class="app">
    <header class="topbar">
      <button class="brand" aria-label="EpisodeScrap 首页" @click="navigate('scan')">
        <span class="reel"><AppIcon name="clap" :size="15" /></span>
        <span class="brand-text">
          <span class="brand-name">EPISODE<span>SCRAP</span></span>
          <span class="brand-sub">MEDIA WORKBENCH</span>
        </span>
      </button>

      <div class="topbar-mid">
        <span class="rec"><i />LIVE</span>
        <span class="tc">{{ timecode }}</span>
        <span class="tc-sub">24 FPS · REC.709</span>
        <span class="mid-line" />
        <span class="source-pill">
          <i />
          <span>SOURCE</span>
          <b>{{ sourceLabel }} · {{ sourceValue }}</b>
        </span>
      </div>

      <div class="topbar-actions">
        <button class="icon-btn" title="任务中心" @click="navigate('tasks')">
          <AppIcon name="tasks" :size="16" />
          <span v-if="runningTasks > 0" class="bubble">{{ runningTasks }}</span>
        </button>
        <button class="icon-btn" title="设置" @click="navigate('settings')">
          <AppIcon name="settings" :size="16" />
        </button>
      </div>
    </header>

    <aside class="rail">
      <div class="rail-label">WORKFLOW / 工作流</div>
      <nav class="steps">
        <button
          v-for="step in steps"
          :key="step.name"
          class="step"
          :class="{ on: route.name === step.name }"
          :disabled="step.disabled"
          :title="step.disabled ? '请先完成上一步' : step.label"
          :aria-label="step.label"
          @click="navigate(step.name, step.disabled)"
        >
          <span class="num">{{ step.num }}</span>
          <AppIcon class="step-ic" :name="step.icon" :size="17" />
          <span>
            <b>{{ step.label }}</b>
            <small>{{ step.en }}</small>
          </span>
          <span class="count">{{ step.count }}</span>
        </button>
      </nav>

      <div class="rail-sep">UTILITIES</div>
      <button
        class="rail-link"
        :class="{ on: route.name === 'refresh' }"
        aria-label="刷新媒体库"
        title="刷新媒体库"
        @click="navigate('refresh')"
      >
        <AppIcon name="refresh" :size="16" />
        <span>刷新媒体库</span>
      </button>

      <div class="rail-spacer" />

      <div class="rail-meta">
        <div class="meta-row"><span>LIBRARY</span><b>{{ store.files.length }}</b></div>
        <div class="meta-row"><span>IN QUEUE</span><b class="amber">{{ inQueue }}</b></div>
        <div class="film-strip" aria-hidden="true">
          <i v-for="index in 12" :key="index" :class="{ on: index <= highlights }" />
        </div>
        <div class="meta-note"><span>SYSTEM NOMINAL</span><span>v{{ version }}</span></div>
      </div>

      <nav class="rail-nav">
        <button
          class="rail-link"
          :class="{ on: route.name === 'tasks' }"
          aria-label="任务中心"
          title="任务中心"
          @click="navigate('tasks')"
        >
          <AppIcon name="tasks" :size="16" />
          <span>任务中心</span>
          <em v-if="runningTasks > 0">{{ runningTasks }}</em>
        </button>
        <button
          class="rail-link"
          :class="{ on: route.name === 'settings' }"
          aria-label="设置"
          title="设置"
          @click="navigate('settings')"
        >
          <AppIcon name="settings" :size="16" />
          <span>设置</span>
        </button>
      </nav>
    </aside>

    <main>
      <div class="page-wrap">
        <router-view v-slot="{ Component }">
          <Transition name="page" mode="out-in">
            <component :is="Component" />
          </Transition>
        </router-view>
      </div>
    </main>
  </div>
</template>
