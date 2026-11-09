<script setup lang="ts">
import { onBeforeUnmount, watch } from 'vue'

import AppIcon from '@/components/AppIcon.vue'

const props = withDefaults(defineProps<{ open: boolean; title?: string; width?: number }>(), {
  width: 480,
})
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
        class="fixed inset-0 z-[85] bg-black/55 backdrop-blur-[2px]"
        @mousedown.self="emit('close')"
      >
        <Transition name="drawer" appear>
          <aside
            v-if="open"
            class="absolute right-0 top-0 flex h-full w-full flex-col border-l border-line bg-elevated shadow-[var(--shadow-float)]"
            :style="{ maxWidth: `${width}px` }"
            role="dialog"
            aria-modal="true"
          >
            <header class="flex items-center gap-3 border-b border-line px-5 py-3.5">
              <h2 class="flex-1 text-[15px] font-semibold text-ink">{{ title }}</h2>
              <button class="icon-btn -mr-2" aria-label="关闭" @click="emit('close')">
                <AppIcon name="x" :size="16" />
              </button>
            </header>
            <div class="flex-1 overflow-y-auto px-5 py-4">
              <slot />
            </div>
            <footer
              v-if="$slots.footer"
              class="flex items-center justify-end gap-2 border-t border-line px-5 py-3"
            >
              <slot name="footer" />
            </footer>
          </aside>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>
