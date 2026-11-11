<script setup lang="ts">
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  watch,
} from 'vue'

import AppIcon from '@/components/AppIcon.vue'

interface OptionItem {
  value: string | number
  label: string
  disabled?: boolean
}

const props = withDefaults(
  defineProps<{
    modelValue: string | number | null
    options?: OptionItem[]
    placeholder?: string
    disabled?: boolean
  }>(),
  {
    options: () => [],
    placeholder: '选择…',
    disabled: false,
  },
)

const emit = defineEmits<{
  'update:modelValue': [value: string | number | null]
}>()

const open = ref(false)
const triggerEl = ref<HTMLElement | null>(null)
const panelEl = ref<HTMLElement | null>(null)
const highlighted = ref(-1)
const rect = ref({ top: 0, left: 0, width: 0 })

// 从 options prop 或 slot <option> 收集选项
const resolvedOptions = computed<OptionItem[]>(() => {
  if (props.options.length > 0) return props.options
  return []
})

const selectedLabel = computed(() => {
  if (props.modelValue === null || props.modelValue === undefined || props.modelValue === '') {
    return ''
  }
  return resolvedOptions.value.find((o) => o.value === props.modelValue)?.label ?? ''
})

const hasPlaceholderOption = computed(
  () => resolvedOptions.value.some((o) => o.value === ''),
)

function toggle() {
  if (props.disabled) return
  if (open.value) close()
  else openMenu()
}

function openMenu() {
  if (props.disabled) return
  open.value = true
  nextTick(() => {
    updateRect()
    const idx = resolvedOptions.value.findIndex(
      (o) => o.value === props.modelValue,
    )
    highlighted.value = idx >= 0 ? idx : 0
    scrollHighlightedIntoView()
  })
  document.addEventListener('click', onDocumentClick, true)
  window.addEventListener('resize', updateRect)
  window.addEventListener('scroll', updateRect, true)
}

function close() {
  open.value = false
  document.removeEventListener('click', onDocumentClick, true)
  window.removeEventListener('resize', updateRect)
  window.removeEventListener('scroll', updateRect, true)
  // 让 trigger 重新聚焦以便键盘继续操作
  nextTick(() => triggerEl.value?.focus())
}

function updateRect() {
  if (!triggerEl.value) return
  const r = triggerEl.value.getBoundingClientRect()
  rect.value = { top: r.bottom + 4, left: r.left, width: r.width }
}

function scrollHighlightedIntoView() {
  if (!panelEl.value || highlighted.value < 0) return
  const item = panelEl.value.children[highlighted.value] as HTMLElement | undefined
  if (item) item.scrollIntoView({ block: 'nearest' })
}

function onDocumentClick(e: MouseEvent) {
  const target = e.target as Node
  if (
    panelEl.value?.contains(target) ||
    triggerEl.value?.contains(target)
  ) {
    return
  }
  close()
}

function onKeydown(e: KeyboardEvent) {
  if (!open.value) {
    if (e.key === 'Enter' || e.key === ' ' || e.key === 'ArrowDown') {
      e.preventDefault()
      openMenu()
    }
    return
  }

  if (e.key === 'Escape') {
    e.preventDefault()
    close()
    return
  }
  if (e.key === 'ArrowDown') {
    e.preventDefault()
    const next = highlighted.value + 1
    if (next < resolvedOptions.value.length) {
      highlighted.value = next
      scrollHighlightedIntoView()
    }
    return
  }
  if (e.key === 'ArrowUp') {
    e.preventDefault()
    const prev = highlighted.value - 1
    if (prev >= 0) {
      highlighted.value = prev
      scrollHighlightedIntoView()
    }
    return
  }
  if (e.key === 'Enter') {
    e.preventDefault()
    if (highlighted.value >= 0 && highlighted.value < resolvedOptions.value.length) {
      select(resolvedOptions.value[highlighted.value])
    }
  }
}

function select(opt: OptionItem) {
  if (opt.disabled) return
  emit('update:modelValue', opt.value)
  close()
}

function onOptionClick(opt: OptionItem) {
  select(opt)
}

// 当外部 modelValue 变化时，如果组件打开就同步高亮
watch(
  () => props.modelValue,
  (v) => {
    if (!open.value) return
    const idx = resolvedOptions.value.findIndex((o) => o.value === v)
    if (idx >= 0) {
      highlighted.value = idx
      scrollHighlightedIntoView()
    }
  },
)

onMounted(() => {
  triggerEl.value?.addEventListener('keydown', onKeydown)
})

onBeforeUnmount(() => {
  triggerEl.value?.removeEventListener('keydown', onKeydown)
  close()
})
</script>

<template>
  <div class="relative">
    <button
      ref="triggerEl"
      type="button"
      class="select block flex items-center justify-between gap-2 text-left"
      :class="{ 'cursor-not-allowed opacity-50': disabled }"
      :aria-expanded="open"
      :aria-haspopup="true"
      :disabled="disabled"
      @click="toggle"
    >
      <span
        class="min-w-0 flex-1 truncate"
        :class="!selectedLabel ? 'text-[var(--text-tertiary)]' : ''"
      >
        {{ selectedLabel || placeholder }}
      </span>
      <AppIcon
        name="chevron-down"
        :size="13"
        class="flex-none transition-transform duration-150"
        :class="open ? 'rotate-180' : ''"
      />
    </button>

    <Teleport to="body">
      <div
        v-if="open"
        ref="panelEl"
        class="fixed z-[100] overflow-hidden rounded-lg border border-[var(--border-strong)] bg-[var(--bg-elevated)] shadow-[var(--shadow-float)]"
        :style="{
          top: `${rect.top}px`,
          left: `${rect.left}px`,
          width: `${rect.width}px`,
          maxHeight: '240px',
          overflowY: 'auto',
        }"
        role="listbox"
      >
        <template v-if="resolvedOptions.length === 0">
          <div class="px-3 py-2 text-xs text-[var(--text-tertiary)]">无选项</div>
        </template>
        <template v-else>
          <button
            v-for="(opt, idx) in resolvedOptions"
            :key="String(opt.value)"
            type="button"
            class="group flex w-full items-center justify-between gap-2 px-3 py-2 text-left text-[13px] transition-colors"
            :class="[
              opt.disabled
                ? 'cursor-not-allowed text-[var(--text-tertiary)] opacity-50'
                : 'hover:bg-[var(--bg-surface)]',
              highlighted === idx && !opt.disabled ? 'bg-[var(--bg-surface)]' : '',
              modelValue === opt.value && !hasPlaceholderOption
                ? 'font-medium text-[var(--accent)]'
                : 'text-[var(--text-primary)]',
            ]"
            role="option"
            :aria-selected="modelValue === opt.value"
            @click="onOptionClick(opt)"
            @mouseenter="highlighted = idx"
          >
            <span class="min-w-0 flex-1 truncate">{{ opt.label }}</span>
            <AppIcon
              v-if="modelValue === opt.value && !opt.disabled"
              name="check"
              :size="13"
              class="flex-none text-[var(--accent)]"
            />
          </button>
        </template>
      </div>
    </Teleport>
  </div>
</template>
