<script setup lang="ts">
withDefaults(
  defineProps<{
    modelValue: boolean
    label?: string
    size?: 'md' | 'sm'
    disabled?: boolean
  }>(),
  { label: '', size: 'md', disabled: false },
)
const emit = defineEmits<{ 'update:modelValue': [value: boolean] }>()
</script>

<template>
  <label class="toggle" :class="{ sm: size === 'sm' }">
    <input
      type="checkbox"
      :checked="modelValue"
      :disabled="disabled"
      @change="emit('update:modelValue', ($event.target as HTMLInputElement).checked)"
    />
    <span class="track" />
    <span v-if="label" class="toggle-text">{{ label }}</span>
  </label>
</template>
