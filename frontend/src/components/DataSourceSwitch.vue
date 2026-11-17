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
  <div class="seg" role="group" aria-label="数据源">
    <button
      type="button"
      class="seg-btn"
      :class="{ on: modelValue === 'local' }"
      :disabled="disabled"
      @click="pick('local')"
    >
      LOCAL · 本地
    </button>
    <button
      type="button"
      class="seg-btn"
      :class="{ on: modelValue === 'openlist' }"
      :disabled="disabled || !hasOpenList"
      :title="hasOpenList ? '使用 OpenList 云盘' : '尚未配置 OpenList 实例'"
      @click="pick('openlist')"
    >
      OPENLIST · 云盘
    </button>
  </div>
</template>
