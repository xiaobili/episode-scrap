<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ status: string; text?: string }>()

const map: Record<string, { label: string; tone: string }> = {
  pending: { label: '待处理', tone: 'muted' },
  scanned: { label: '已扫描', tone: 'muted' },
  parsed: { label: '已解析', tone: 'info' },
  matched: { label: '已匹配', tone: 'accent' },
  unmatched: { label: '未匹配', tone: 'warning' },
  ready: { label: '可执行', tone: 'success' },
  renamed: { label: '已重命名', tone: 'success' },
  success: { label: '成功', tone: 'success' },
  conflict: { label: '冲突', tone: 'warning' },
  skipped: { label: '跳过', tone: 'muted' },
  error: { label: '失败', tone: 'danger' },
  failed: { label: '失败', tone: 'danger' },
  running: { label: '运行中', tone: 'info' },
  completed: { label: '已完成', tone: 'success' },
  rolled_back: { label: '已撤销', tone: 'muted' },
}

const toneClass: Record<string, string> = {
  accent: 'tag-accent',
  success: 'tag-success',
  warning: 'tag-warning',
  danger: 'tag-danger',
  info: 'tag-info',
  muted: '',
}

const current = computed(
  () => map[props.status] ?? { label: props.status, tone: 'muted' },
)
</script>

<template>
  <span class="tag" :class="toneClass[current.tone]">
    <span class="h-1.5 w-1.5 rounded-full bg-current opacity-80" />
    {{ text ?? current.label }}
  </span>
</template>
