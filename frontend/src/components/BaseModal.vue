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
      <div v-if="open" class="modal open" @mousedown.self="emit('close')">
        <div
          class="dialog"
          :style="{ maxWidth: `${width}px` }"
          role="dialog"
          aria-modal="true"
        >
          <header class="dialog-head">
            <div class="min-w-0 flex-1">
              <div class="dialog-title">{{ title }}</div>
              <p v-if="subtitle" class="mt-1 text-xs text-muted">{{ subtitle }}</p>
            </div>
            <button class="icon-btn" aria-label="关闭" @click="emit('close')">
              <AppIcon name="x" :size="15" />
            </button>
          </header>
          <div class="dialog-body">
            <slot />
          </div>
          <footer v-if="$slots.footer" class="dialog-foot">
            <slot name="footer" />
          </footer>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
