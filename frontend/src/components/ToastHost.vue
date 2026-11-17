<script setup lang="ts">
import AppIcon from '@/components/AppIcon.vue'
import { useToast } from '@/composables/useToast'

const { state, dismiss } = useToast()

const icons: Record<string, string> = {
  success: 'check-circle',
  error: 'alert',
  info: 'sparkles',
}
const tones: Record<string, string> = {
  success: 'text-success',
  error: 'text-danger',
  info: 'text-info',
}
</script>

<template>
  <Teleport to="body">
    <div class="toasts" aria-live="polite">
      <TransitionGroup name="modal">
        <div
          v-for="item in state.items"
          :key="item.id"
          class="toast"
          :class="item.type === 'success' ? 'ok' : item.type === 'error' ? 'err' : ''"
        >
          <AppIcon :name="icons[item.type]" :size="14" :class="tones[item.type]" />
          <p class="flex-1 leading-5 text-ink">{{ item.message }}</p>
          <button class="text-faint hover:text-ink" aria-label="关闭提示" @click="dismiss(item.id)">
            <AppIcon name="x" :size="13" />
          </button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>
