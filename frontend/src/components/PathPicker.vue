<script setup lang="ts">
import { ref } from 'vue'

import AppIcon from '@/components/AppIcon.vue'
import DirectoryBrowser from '@/components/DirectoryBrowser.vue'
import type { SourceType } from '@/types'

defineProps<{
  modelValue: string
  sourceType: SourceType
  openlistId: number | null
  recursive: boolean
  disabled?: boolean
}>()
const emit = defineEmits<{
  'update:modelValue': [value: string]
  'update:recursive': [value: boolean]
}>()

const browserOpen = ref(false)
</script>

<template>
  <div class="flex flex-col gap-3 sm:flex-row sm:items-end">
    <div class="min-w-0 flex-1">
      <label class="label">{{ sourceType === 'openlist' ? '云盘路径' : '本地路径' }}</label>
      <div class="flex gap-2">
        <input
          class="input font-mono text-xs"
          :value="modelValue"
          :disabled="disabled"
          :placeholder="sourceType === 'openlist' ? '/媒体/剧集' : '/data/media/tv'"
          spellcheck="false"
          @input="emit('update:modelValue', ($event.target as HTMLInputElement).value)"
        />
        <button
          class="btn flex-none"
          :disabled="disabled || (sourceType === 'openlist' && !openlistId)"
          @click="browserOpen = true"
        >
          <AppIcon name="folder" :size="14" />
          浏览
        </button>
      </div>
    </div>

    <label class="flex h-8 cursor-pointer select-none items-center gap-2 text-[13px] text-muted">
      <input
        type="checkbox"
        class="h-4 w-4 accent-accent"
        :checked="recursive"
        :disabled="disabled"
        @change="emit('update:recursive', ($event.target as HTMLInputElement).checked)"
      />
      递归子目录
    </label>

    <DirectoryBrowser
      :open="browserOpen"
      :mode="sourceType"
      :openlist-id="openlistId"
      :initial-path="modelValue"
      :title="sourceType === 'openlist' ? '选择云盘目录' : '选择本地目录'"
      @close="browserOpen = false"
      @select="emit('update:modelValue', $event)"
    />
  </div>
</template>
