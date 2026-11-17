<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import { api } from '@/api/client'
import AppIcon from '@/components/AppIcon.vue'
import BaseModal from '@/components/BaseModal.vue'
import ErrorBanner from '@/components/ErrorBanner.vue'
import type { SourceType, TreeEntry, TreeResponse } from '@/types'

const props = withDefaults(
  defineProps<{
    open: boolean
    mode: SourceType
    openlistId: number | null
    initialPath?: string
    title?: string
  }>(),
  { initialPath: '', title: '选择目录' },
)
const emit = defineEmits<{ close: []; select: [path: string] }>()

const path = ref('')
const tree = ref<TreeResponse | null>(null)
const loading = ref(false)
const error = ref('')

const entries = computed<TreeEntry[]>(() => {
  const list = tree.value?.entries ?? []
  return [...list].sort((a, b) => Number(b.is_dir) - Number(a.is_dir) || a.name.localeCompare(b.name))
})

const crumbs = computed(() => {
  const value = path.value
  const parts = value.split('/').filter(Boolean)
  const absolute = value.startsWith('/')
  const items = parts.map((label, index) => ({
    label,
    path: (absolute ? '/' : '') + parts.slice(0, index + 1).join('/'),
  }))
  return [
    { label: props.mode === 'openlist' ? '云盘根目录' : '根目录', path: absolute ? '/' : '' },
    ...items,
  ]
})

async function load(target: string, force = false) {
  if (props.mode === 'openlist' && !props.openlistId) {
    error.value = '请先选择 OpenList 实例'
    return
  }
  loading.value = true
  error.value = ''
  try {
    tree.value =
      props.mode === 'openlist'
        ? await api.getOpenListTree(props.openlistId as number, target, force)
        : await api.getLocalTree(target)
    path.value = tree.value.path
  } catch (err) {
    error.value = err instanceof Error ? err.message : '目录读取失败'
  } finally {
    loading.value = false
  }
}

watch(
  () => [props.open, props.mode, props.openlistId] as const,
  ([open]) => {
    if (open) {
      tree.value = null
      void load(props.initialPath)
    }
  },
  { immediate: true },
)

function enter(entry: TreeEntry) {
  if (entry.is_dir) void load(entry.path)
}

function choose() {
  emit('select', path.value)
  emit('close')
}
</script>

<template>
  <BaseModal :open="open" :title="title" :width="680" @close="emit('close')">
    <div class="flex items-center gap-2">
      <div class="crumbs min-w-0 flex-1">
        <template v-for="(crumb, index) in crumbs" :key="crumb.path + index">
          <AppIcon v-if="index > 0" name="chevron-right" :size="10" class="slash flex-none" />
          <button @click="load(crumb.path)">{{ crumb.label }}</button>
        </template>
      </div>
      <button class="btn btn-sm flex-none" :disabled="loading" @click="load(path, true)">
        <AppIcon name="refresh" :size="13" :spin="loading" />
        刷新
      </button>
    </div>

    <ErrorBanner v-if="error" class="mt-3" :message="error" retryable @retry="load(path)" />

    <div class="folder-grid mt-3">
      <div v-if="loading" class="grid gap-1.5 sm:col-span-2">
        <div v-for="index in 6" :key="index" class="h-8 animate-pulse rounded bg-[var(--surface-2)]" />
      </div>
      <p v-else-if="entries.length === 0" class="col-span-2 py-16 text-center text-[13px] text-muted">
        该目录下没有子目录
      </p>
      <template v-else>
        <button
          v-for="entry in entries"
          :key="entry.path"
          class="folder"
          :class="entry.is_dir ? '' : 'cursor-default opacity-60'"
          :title="entry.path"
          @click="enter(entry)"
        >
          <AppIcon :name="entry.is_dir ? 'folder' : 'file'" :size="14" />
          <span class="truncate">{{ entry.name }}</span>
          <AppIcon
            v-if="entry.is_dir"
            name="chevron-right"
            :size="12"
            class="ml-auto flex-none opacity-40"
          />
        </button>
      </template>
    </div>

    <div class="mt-3 flex items-center gap-2">
      <span class="min-w-0 flex-1 truncate font-mono text-xs text-faint">
        当前：{{ path || '（根目录）' }}
      </span>
      <button class="btn btn-ghost" @click="emit('close')">取消</button>
      <button class="btn btn-amber" :disabled="loading" @click="choose">选择此目录</button>
    </div>
  </BaseModal>
</template>
