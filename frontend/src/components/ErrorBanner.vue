<script setup lang="ts">
import AppIcon from '@/components/AppIcon.vue'

withDefaults(defineProps<{ message: string; title?: string; retryable?: boolean }>(), {
  title: '操作失败',
  retryable: false,
})
const emit = defineEmits<{ retry: [] }>()
</script>

<template>
  <div class="warn-note" role="alert" style="border-color: rgba(226, 101, 79, 0.35); background: rgba(226, 101, 79, 0.08)">
    <AppIcon name="alert" :size="15" class="mt-0.5 flex-none" style="color: var(--red)" />
    <div class="min-w-0 flex-1">
      <p class="text-[13px] font-medium text-ink">{{ title }}</p>
      <p class="mt-0.5 break-words text-xs leading-5 text-muted">{{ message }}</p>
    </div>
    <button v-if="retryable" class="btn btn-sm flex-none" @click="emit('retry')">重试</button>
  </div>
</template>
