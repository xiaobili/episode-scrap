<script setup lang="ts">
import { onBeforeUnmount, watch } from 'vue'

import AppIcon from '@/components/AppIcon.vue'

const props = withDefaults(
  defineProps<{
    open: boolean
    title?: string
    subtitle?: string
    width?: number
  }>(),
  { width: 620 },
)
const emit = defineEmits<{ close: [] }>()

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') emit('close')
}

watch(
  () => props.open,
  (open) => {
    if (open) {
      document.addEventListener('keydown', onKeydown)
      document.body.style.overflow = 'hidden'
    } else {
      document.removeEventListener('keydown', onKeydown)
      document.body.style.overflow = ''
    }
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  document.removeEventListener('keydown', onKeydown)
  document.body.style.overflow = ''
})
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div
        v-if="open"
        class="fixed inset-0 z-[90] grid place-items-center overflow-y-auto bg-black/60 p-4 backdrop-blur-[2px]"
        @mousedown.self="emit('close')"
      >
        <div
          class="panel my-auto w-full overflow-hidden shadow-[var(--shadow-float)]"
          :style="{ maxWidth: `${width}px` }"
          role="dialog"
          aria-modal="true"
        >
          <header class="flex items-start gap-3 border-b border-line px-5 py-3.5">
            <div class="min-w-0 flex-1">
              <h2 class="text-[15px] font-semibold text-ink">{{ title }}</h2>
              <p v-if="subtitle" class="mt-0.5 text-xs text-muted">{{ subtitle }}</p>
            </div>
            <button class="icon-btn -mr-2 -mt-1" aria-label="关闭" @click="emit('close')">
              <AppIcon name="x" :size="16" />
            </button>
          </header>
          <div class="max-h-[70vh] overflow-y-auto px-5 py-4">
            <slot />
          </div>
          <footer
            v-if="$slots.footer"
            class="flex items-center justify-end gap-2 border-t border-line px-5 py-3"
          >
            <slot name="footer" />
          </footer>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
