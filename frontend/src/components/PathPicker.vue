<script setup lang="ts">
import { computed, ref } from 'vue'

import AppIcon from '@/components/AppIcon.vue'
import DirectoryBrowser from '@/components/DirectoryBrowser.vue'
import SelectMenu from '@/components/SelectMenu.vue'
import type { SourceType } from '@/types'

const props = defineProps<{
  modelValue: string
  sourceType: SourceType
  openlistId: number | null
  disabled?: boolean
  /** 本地模式下显示的允许访问的根目录列表 */
  allowedRoots?: string[]
}>()
const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const browserOpen = ref(false)

const showRootSelector = computed(
  () => props.sourceType === 'local' && (props.allowedRoots?.length ?? 0) > 0,
)

const rootOptions = computed(() =>
  (props.allowedRoots ?? []).map((r) => ({ value: r, label: r })),
)

const modelValueLocal = computed({
  get: () => props.modelValue,
  set: (v: string | number | null) => emit('update:modelValue', String(v ?? '')),
})
</script>

<template>
  <div class="grid gap-3">
    <div class="field">
      <label>
        {{ sourceType === 'openlist' ? '云盘路径' : '本地路径' }}
        <span>PATH</span>
      </label>
      <div class="flex items-center gap-2">
        <SelectMenu
          v-if="showRootSelector"
          v-model="modelValueLocal"
          class="min-w-0 flex-1"
          :options="rootOptions"
          :disabled="disabled"
          placeholder="选择根目录"
        />

        <div v-else class="input-group min-w-0 flex-1">
          <AppIcon name="folder" :size="14" />
          <input
            v-if="sourceType === 'local'"
            :value="modelValue"
            :disabled="disabled"
            placeholder="/data/media/tv"
            spellcheck="false"
            aria-label="本地路径"
            @input="emit('update:modelValue', ($event.target as HTMLInputElement).value)"
          />
          <input v-else :value="modelValue" disabled placeholder="点击右侧浏览选择目录" aria-label="云盘路径" />
        </div>

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
