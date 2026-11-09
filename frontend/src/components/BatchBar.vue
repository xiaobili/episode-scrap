<script setup lang="ts">
import AppIcon from '@/components/AppIcon.vue'

withDefaults(
  defineProps<{
    count: number
    nextLabel?: string
    nextDisabled?: boolean
    showNext?: boolean
  }>(),
  { nextLabel: '下一步', nextDisabled: false, showNext: true },
)
const emit = defineEmits<{ clear: []; next: [] }>()
</script>

<template>
  <Transition name="fade">
    <div
      v-if="count > 0"
      class="fixed bottom-0 left-0 right-0 z-30 flex h-14 items-center gap-3 border-t border-line bg-[color-mix(in_srgb,var(--bg-surface)_92%,transparent)] px-4 backdrop-blur-xl md:left-[var(--sidebar-width,224px)] md:px-7"
    >
      <span class="text-[13px] text-muted">
        已选 <span class="font-mono font-semibold text-ink">{{ count }}</span> 项
      </span>
      <button class="btn btn-ghost btn-sm" @click="emit('clear')">清空选择</button>

      <div class="flex flex-1 items-center justify-end gap-2">
        <slot />
        <button
          v-if="showNext"
          class="btn btn-primary"
          :disabled="nextDisabled || count === 0"
          @click="emit('next')"
        >
          {{ nextLabel }}
          <AppIcon name="arrow-right" :size="14" />
        </button>
      </div>
    </div>
  </Transition>
</template>
