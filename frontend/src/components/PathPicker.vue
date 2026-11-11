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
  recursive: boolean
  disabled?: boolean
  /** 本地模式下显示的允许访问的根目录列表 */
  allowedRoots?: string[]
}>()
const emit = defineEmits<{
  'update:modelValue': [value: string]
  'update:recursive': [value: boolean]
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
  <div class="flex flex-col gap-2">
    <label class="label">
      {{ sourceType === 'openlist' ? '云盘路径' : '本地路径' }}
    </label>
    <div class="flex items-center gap-2">
      <!-- 本地栏：只有下拉菜单 -->
      <SelectMenu
        v-if="showRootSelector"
        v-model="modelValueLocal"
        class="min-w-0 flex-1"
        :options="rootOptions"
        :disabled="disabled"
        placeholder="选择根目录"
      />

      <!-- 无白名单回退：输入框 -->
      <input
        v-else-if="sourceType === 'local'"
        class="input min-w-0 flex-1 font-mono text-xs"
        :value="modelValue"
        :disabled="disabled"
        placeholder="/data/media/tv"
        spellcheck="false"
        @input="emit('update:modelValue', ($event.target as HTMLInputElement).value)"
      />

      <!-- OpenList 栏：禁用输入框，只能通过浏览选择 -->
      <input
        v-else
        class="input min-w-0 flex-1 font-mono text-xs"
        :value="modelValue"
        disabled
        placeholder="点击右侧浏览选择目录"
      />

      <button
        class="btn flex-none"
        :disabled="disabled || (sourceType === 'openlist' && !openlistId)"
        @click="browserOpen = true"
      >
        <AppIcon name="folder" :size="14" />
        浏览
      </button>
      <label class="flex-none flex h-8 cursor-pointer select-none items-center gap-2 text-[13px] text-muted">
        <input
          type="checkbox"
          class="h-4 w-4 accent-accent"
          :checked="recursive"
          :disabled="disabled"
          @change="emit('update:recursive', ($event.target as HTMLInputElement).checked)"
        />
        递归子目录
      </label>
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
