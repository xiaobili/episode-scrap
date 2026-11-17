<script setup lang="ts">
import AppIcon from '@/components/AppIcon.vue'

withDefaults(
  defineProps<{
    count: number
    total?: number
    chips?: string[]
    nextLabel?: string
    nextDisabled?: boolean
    showNext?: boolean
  }>(),
  { nextLabel: '下一步', nextDisabled: false, showNext: true, chips: () => [] },
)
const emit = defineEmits<{ clear: []; next: [] }>()
</script>

<template>
  <Transition name="fade">
    <div v-if="count > 0" class="batchbar">
      <div class="batch-count">
        <b>{{ count }}</b>
        <span>SELECTED / {{ total ?? count }}</span>
      </div>

      <div v-if="chips.length" class="batch-chips">
        <span v-for="chip in chips.slice(0, 4)" :key="chip">{{ chip }}</span>
      </div>

      <div class="batch-actions">
        <button class="btn btn-xs btn-ghost" @click="emit('clear')">清空</button>
        <slot />
        <button
          v-if="showNext"
          class="btn btn-xs btn-primary"
          :disabled="nextDisabled || count === 0"
          @click="emit('next')"
        >
          {{ nextLabel }}
          <AppIcon name="arrow-right" :size="12" />
        </button>
      </div>
    </div>
  </Transition>
</template>
