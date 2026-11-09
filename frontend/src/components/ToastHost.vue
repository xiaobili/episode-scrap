<script setup lang="ts">
import AppIcon from '@/components/AppIcon.vue'
import { useToast } from '@/composables/useToast'

const { state, dismiss } = useToast()

const styles: Record<string, string> = {
  success: 'border-success/40 text-success',
  error: 'border-danger/40 text-danger',
  info: 'border-info/40 text-info',
}
const icons: Record<string, string> = {
  success: 'check-circle',
  error: 'alert',
  info: 'sparkles',
}
</script>

<template>
  <Teleport to="body">
    <div class="pointer-events-none fixed bottom-5 right-5 z-[120] flex w-[340px] flex-col gap-2">
      <TransitionGroup name="modal">
        <div
          v-for="item in state.items"
          :key="item.id"
          class="pointer-events-auto flex items-start gap-2.5 rounded-lg border bg-elevated px-3.5 py-3 shadow-[var(--shadow-float)]"
          :class="styles[item.type]"
        >
          <AppIcon :name="icons[item.type]" :size="16" class="mt-0.5 shrink-0" />
          <p class="flex-1 text-[13px] leading-5 text-ink">{{ item.message }}</p>
          <button class="text-faint hover:text-ink" @click="dismiss(item.id)">
            <AppIcon name="x" :size="14" />
          </button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>
