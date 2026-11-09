<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { api } from '@/api/client'
import AppIcon from '@/components/AppIcon.vue'
import StepNav from '@/components/StepNav.vue'
import { useToast } from '@/composables/useToast'
import { useWorkflowStore } from '@/stores/workflow'

interface NavItem {
  name: string
  label: string
  icon: string
  badge?: number
}

const store = useWorkflowStore()
const route = useRoute()
const router = useRouter()
const toast = useToast()

const theme = ref(document.documentElement.dataset.theme === 'light' ? 'light' : 'dark')
const collapsed = ref(localStorage.getItem('episode-scrap-sidebar') === 'collapsed')
const mobileOpen = ref(false)
const runningTasks = ref(0)

const workbench = computed<NavItem[]>(() => [
  { name: 'scan', label: '扫描', icon: 'scan', badge: store.stepCounts.scan },
  { name: 'parse', label: '解析', icon: 'parse', badge: store.stepCounts.parse },
  { name: 'scrape', label: '刮削', icon: 'scrape', badge: store.stepCounts.scrape },
  { name: 'rename', label: '重命名', icon: 'rename', badge: store.stepCounts.rename },
  { name: 'refresh', label: '刷新', icon: 'refresh' },
])

const secondary = computed<NavItem[]>(() => [
  { name: 'tasks', label: '任务中心', icon: 'tasks', badge: runningTasks.value },
  { name: 'settings', label: '设置', icon: 'settings' },
])

function toggleTheme() {
  theme.value = theme.value === 'dark' ? 'light' : 'dark'
  document.documentElement.dataset.theme = theme.value
  localStorage.setItem('episode-scrap-theme', theme.value)
}

function toggleCollapsed() {
  collapsed.value = !collapsed.value
  localStorage.setItem('episode-scrap-sidebar', collapsed.value ? 'collapsed' : 'expanded')
}

function navigate(name: string) {
  mobileOpen.value = false
  if (route.name !== name) router.push({ name })
}

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') {
    store.clearSelection()
    mobileOpen.value = false
  }
}

async function loadTaskBadge() {
  try {
    const tasks = await api.getTasks()
    runningTasks.value = tasks.filter((task) => task.status === 'running' || task.status === 'pending')
      .length
  } catch {
    runningTasks.value = 0
  }
}

watch(
  () => route.name,
  () => {
    mobileOpen.value = false
    if (route.name === 'tasks') loadTaskBadge()
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
  <div
    class="flex h-full w-full flex-col"
    :style="{ '--sidebar-width': collapsed ? '64px' : '224px' }"
  >
    <header
      class="flex h-14 flex-none items-center gap-3 border-b border-line bg-[color-mix(in_srgb,var(--bg-base)_88%,transparent)] px-4 backdrop-blur-xl md:gap-5 md:px-5"
    >
      <button class="icon-btn md:hidden" aria-label="打开导航" @click="mobileOpen = true">
        <AppIcon name="panel-left" :size="17" />
      </button>

      <button
        class="flex w-[190px] flex-none items-center gap-2.5 text-left"
        @click="navigate('scan')"
      >
        <span
          class="grid h-7 w-7 place-items-center rounded-[7px] border border-[rgba(24,194,168,.38)] bg-gradient-to-br from-[rgba(24,194,168,.22)] to-[rgba(24,194,168,.05)] text-accent"
        >
          <AppIcon name="film" :size="15" />
        </span>
        <span class="leading-tight">
          <span class="block text-[14.5px] font-semibold tracking-[0.01em]">
            Episode<span class="text-accent">Scrap</span>
          </span>
          <span class="hidden text-[9.5px] uppercase tracking-[0.18em] text-faint sm:block">
            Media Workbench
          </span>
        </span>
      </button>

      <div class="flex-1 overflow-hidden">
        <StepNav />
      </div>

      <div class="flex flex-none items-center gap-1">
        <button
          class="icon-btn"
          :aria-label="theme === 'dark' ? '切换到浅色主题' : '切换到深色主题'"
          @click="toggleTheme"
        >
          <AppIcon :name="theme === 'dark' ? 'sun' : 'moon'" :size="16" />
        </button>
        <button class="icon-btn" aria-label="任务中心" @click="navigate('tasks')">
          <AppIcon name="tasks" :size="16" />
          <span
            v-if="runningTasks > 0"
            class="absolute right-[7px] top-[7px] h-[5px] w-[5px] rounded-full bg-accent shadow-[0_0_0_2px_var(--bg-base)]"
          />
        </button>
        <button class="icon-btn" aria-label="设置" @click="navigate('settings')">
          <AppIcon name="settings" :size="16" />
        </button>
      </div>
    </header>

    <div class="flex min-h-0 flex-1">
      <Transition name="fade">
        <div
          v-if="mobileOpen"
          class="fixed inset-0 z-40 bg-black/55 backdrop-blur-[1px] md:hidden"
          @click="mobileOpen = false"
        />
      </Transition>

      <aside
        class="fixed inset-y-0 left-0 z-50 flex w-[224px] flex-none flex-col border-r border-line bg-surface px-3 pb-4 pt-3 transition-transform md:static md:z-auto md:translate-x-0 md:bg-[color-mix(in_srgb,var(--bg-surface)_55%,transparent)]"
        :class="[
          mobileOpen ? 'translate-x-0' : '-translate-x-full',
          collapsed ? 'md:w-16' : 'md:w-[224px]',
        ]"
      >
        <div class="mb-1 flex items-center justify-between px-2">
          <span v-if="!collapsed" class="text-[9.5px] uppercase tracking-[0.16em] text-faint">
            工作台
          </span>
          <button
            class="icon-btn hidden h-7 w-7 md:grid"
            :aria-label="collapsed ? '展开侧栏' : '收起侧栏'"
            @click="toggleCollapsed"
          >
            <AppIcon name="panel-left" :size="15" />
          </button>
        </div>

        <nav class="flex flex-col gap-0.5">
          <button
            v-for="item in workbench"
            :key="item.name"
            class="group relative flex h-10 items-center gap-2.5 rounded-md px-2.5 text-[13.5px] font-medium transition"
            :class="
              route.name === item.name
                ? 'bg-[var(--accent-soft)] text-ink'
                : 'text-muted hover:bg-[var(--bg-elevated)] hover:text-ink'
            "
            :title="collapsed ? item.label : undefined"
            @click="navigate(item.name)"
          >
            <span
              v-if="route.name === item.name"
              class="absolute -left-3 top-2.5 bottom-2.5 w-[3px] rounded-r bg-accent"
            />
            <AppIcon
              :name="item.icon"
              :size="17"
              :class="route.name === item.name ? 'opacity-100' : 'opacity-80'"
            />
            <span v-if="!collapsed" class="truncate">{{ item.label }}</span>
            <span
              v-if="item.badge && item.badge > 0"
              class="rounded-full px-1.5 py-px font-mono text-[10.5px]"
              :class="
                collapsed
                  ? 'absolute right-1 top-1 bg-accent px-1 text-[9px] text-[#06231f]'
                  : route.name === item.name
                    ? 'ml-auto bg-[rgba(24,194,168,.18)] text-accent'
                    : 'ml-auto bg-[rgba(255,255,255,.055)] text-faint'
              "
            >
              {{ item.badge }}
            </span>
          </button>
        </nav>

        <div class="flex-1" />

        <nav class="flex flex-col gap-0.5 border-t border-line pt-2">
          <button
            v-for="item in secondary"
            :key="item.name"
            class="relative flex h-10 items-center gap-2.5 rounded-md px-2.5 text-[13.5px] font-medium text-muted transition hover:bg-[var(--bg-elevated)] hover:text-ink"
            :class="route.name === item.name ? 'bg-[var(--accent-soft)] text-ink' : ''"
            :title="collapsed ? item.label : undefined"
            @click="navigate(item.name)"
          >
            <span
              v-if="route.name === item.name"
              class="absolute -left-3 top-2.5 bottom-2.5 w-[3px] rounded-r bg-accent"
            />
            <AppIcon :name="item.icon" :size="17" class="opacity-80" />
            <span v-if="!collapsed" class="truncate">{{ item.label }}</span>
            <span
              v-if="item.badge && item.badge > 0 && !collapsed"
              class="ml-auto rounded-full bg-[var(--accent-soft)] px-1.5 py-px font-mono text-[10.5px] text-accent"
            >
              {{ item.badge }}
            </span>
          </button>
        </nav>
      </aside>

      <main class="min-w-0 flex-1 overflow-y-auto">
        <div class="mx-auto w-full max-w-[1440px] px-5 pb-28 pt-5 md:px-7 md:pt-6">
          <router-view v-slot="{ Component }">
            <Transition name="fade" mode="out-in">
              <component :is="Component" />
            </Transition>
          </router-view>
        </div>
      </main>
    </div>
  </div>
</template>
