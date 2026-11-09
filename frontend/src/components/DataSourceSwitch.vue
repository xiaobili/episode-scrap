<script setup lang="ts">
import { computed } from 'vue'

import AppIcon from '@/components/AppIcon.vue'
import type { DataSource, SourceType } from '@/types'

const props = defineProps<{
  modelValue: SourceType
  sources: DataSource[]
  disabled?: boolean
}>()
const emit = defineEmits<{ 'update:modelValue': [SourceType] }>()

const hasOpenList = computed(() =>
  props.sources.some((source) => source.type === 'openlist' && source.id !== null),
)

function pick(type: SourceType) {
  if (props.disabled) return
  if (type === 'openlist' && !hasOpenList.value) return
  emit('update:modelValue', type)
}
</script>

<template>
  <div class="inline-flex rounded-md border border-line-strong bg-base p-0.5">
    <button
      class="flex h-7 items-center gap-1.5 rounded px-3 text-xs font-medium transition"
      :class="
        modelValue === 'local'
          ? 'bg-[var(--accent-soft)] text-accent'
          : 'text-muted hover:text-ink'
      "
      :disabled="disabled"
      @click="pick('local')"
    >
      <AppIcon name="folder" :size="13" />
      本地
    </button>
    <button
      class="flex h-7 items-center gap-1.5 rounded px-3 text-xs font-medium transition"
      :class="[
        modelValue === 'openlist'
          ? 'bg-[var(--accent-soft)] text-accent'
          : 'text-muted hover:text-ink',
        !hasOpenList ? 'cursor-not-allowed opacity-45' : '',
      ]"
      :disabled="disabled"
      :title="hasOpenList ? '使用 OpenList 云盘' : '尚未配置 OpenList 实例'"
      @click="pick('openlist')"
    >
      <AppIcon name="cloud" :size="13" />
      OpenList
    </button>
  </div>
</template>
