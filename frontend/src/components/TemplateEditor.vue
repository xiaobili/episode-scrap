<script setup lang="ts">
import { computed, ref } from 'vue'

import AppIcon from '@/components/AppIcon.vue'
import type { MediaFile } from '@/types'

const props = withDefaults(
  defineProps<{ modelValue: string; sample?: MediaFile | null; disabled?: boolean }>(),
  { sample: null, disabled: false },
)
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()

const input = ref<HTMLInputElement | null>(null)

const variables = [
  { name: 'title', label: '剧名' },
  { name: 'year', label: '年份' },
  { name: 'season', label: '季', pad: true },
  { name: 'episode', label: '集', pad: true },
  { name: 'episode_title', label: '集标题' },
  { name: 'resolution', label: '分辨率' },
  { name: 'codec', label: '编码' },
  { name: 'release_group', label: '发布组' },
]
const allowed = new Set(variables.map((item) => item.name))

const demo: Record<string, string | number | null> = {
  title: 'Breaking Bad',
  year: 2008,
  season: 1,
  episode: 3,
  episode_end: null,
  episode_title: "...And the Bag's in the River",
  resolution: '1080p',
  codec: 'x264',
  release_group: 'DEMAND',
}

const meta = computed<Record<string, string | number | null>>(() => {
  if (!props.sample?.parsed) return demo
  return props.sample.parsed as unknown as Record<string, string | number | null>
})

const unknown = computed(() => {
  const found = new Set<string>()
  for (const match of props.modelValue.matchAll(/\{([^}]+)\}/g)) {
    const name = match[1].split(':')[0].trim()
    if (!allowed.has(name)) found.add(name)
  }
  return Array.from(found)
})

const preview = computed(() =>
  props.modelValue.replace(/\{(\w+)(?::(\d+)d)?\}/g, (_match, name: string, width?: string) => {
    const value = meta.value[name]
    if (value === null || value === undefined || value === '') return ''
    if (width && typeof value === 'number') return String(value).padStart(Number(width), '0')
    return String(value)
  }),
)

function insert(name: string, pad?: boolean) {
  const token = pad ? `{${name}:02d}` : `{${name}}`
  const element = input.value
  const start = element?.selectionStart ?? props.modelValue.length
  const end = element?.selectionEnd ?? props.modelValue.length
  const next = props.modelValue.slice(0, start) + token + props.modelValue.slice(end)
  emit('update:modelValue', next)
  requestAnimationFrame(() => {
    element?.focus()
    const cursor = start + token.length
    element?.setSelectionRange(cursor, cursor)
  })
}
</script>

<template>
  <div>
    <div class="flex items-center gap-2">
      <input
        ref="input"
        class="input font-mono text-xs"
        :value="modelValue"
        :disabled="disabled"
        spellcheck="false"
        placeholder="{title} - S{season:02d}E{episode:02d} - {episode_title}"
        @input="emit('update:modelValue', ($event.target as HTMLInputElement).value)"
      />
      <span class="flex-none font-mono text-[11px] text-faint">.mkv</span>
    </div>

    <div class="mt-2 flex flex-wrap items-center gap-1">
      <span class="mr-1 text-[11px] text-faint">插入变量</span>
      <button
        v-for="item in variables"
        :key="item.name"
        class="rounded border border-line px-1.5 py-0.5 font-mono text-[11px] text-muted transition hover:border-accent hover:text-accent"
        :disabled="disabled"
        @click="insert(item.name, item.pad)"
      >
        + {{ item.label }}
      </button>
    </div>

    <p v-if="unknown.length" class="mt-1.5 flex items-center gap-1 text-[11.5px] text-danger">
      <AppIcon name="alert" :size="12" />
      未知变量：{{ unknown.join('、') }}
    </p>

    <div class="mt-2 rounded-md border border-line bg-base px-2.5 py-1.5">
      <span class="mr-2 text-[11px] text-faint">实时示例</span>
      <span class="break-all font-mono text-xs text-ink">
        {{ preview || '（模板为空）' }}.mkv
      </span>
    </div>
  </div>
</template>
