<script setup lang="ts">
import AppIcon from '@/components/AppIcon.vue'

withDefaults(defineProps<{ message: string; title?: string; retryable?: boolean }>(), {
  title: '操作失败',
  retryable: false,
})
const emit = defineEmits<{ retry: [] }>()
</script>

<template>
  <div
    class="flex items-start gap-2.5 rounded-lg border border-[rgba(240,97,109,.35)] bg-[rgba(240,97,109,.08)] px-3.5 py-2.5"
    role="alert"
  >
    <AppIcon name="alert" :size="15" class="mt-0.5 flex-none text-danger" />
    <div class="min-w-0 flex-1">
      <p class="text-[13px] font-medium text-ink">{{ title }}</p>
      <p class="mt-0.5 break-words text-xs leading-5 text-muted">{{ message }}</p>
    </div>
    <button v-if="retryable" class="btn btn-sm flex-none" @click="emit('retry')">重试</button>
  </div>
</template>
