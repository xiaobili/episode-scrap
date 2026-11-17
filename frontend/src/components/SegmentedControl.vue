<script setup lang="ts">
import type { SegValue } from '@/components/ui-types'

withDefaults(
  defineProps<{
    modelValue: SegValue
    options: { value: SegValue; label: string; disabled?: boolean }[]
    size?: 'md' | 'sm'
    ariaLabel?: string
  }>(),
  { size: 'md', ariaLabel: '选项' },
)
const emit = defineEmits<{ 'update:modelValue': [value: SegValue] }>()
</script>

<template>
  <div class="seg" role="group" :aria-label="ariaLabel">
    <button
      v-for="option in options"
      :key="String(option.value)"
      type="button"
      class="seg-btn"
      :class="{ on: modelValue === option.value }"
      :aria-pressed="modelValue === option.value"
      :style="
        size === 'sm'
          ? { height: '24px', padding: '0 9px', fontSize: '9.5px' }
          : undefined
      "
      :disabled="option.disabled"
      @click="emit('update:modelValue', option.value)"
    >
      {{ option.label }}
    </button>
  </div>
</template>
