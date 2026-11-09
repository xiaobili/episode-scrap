<script setup lang="ts">
import BaseModal from '@/components/BaseModal.vue'

withDefaults(
  defineProps<{
    open: boolean
    title: string
    message?: string
    confirmText?: string
    cancelText?: string
    danger?: boolean
    loading?: boolean
  }>(),
  { confirmText: '确认', cancelText: '取消', danger: false, loading: false },
)
const emit = defineEmits<{ confirm: []; cancel: [] }>()
</script>

<template>
  <BaseModal :open="open" :title="title" :width="460" @close="emit('cancel')">
    <p v-if="message" class="whitespace-pre-line text-[13px] leading-6 text-muted">
      {{ message }}
    </p>
    <slot />
    <template #footer>
      <button class="btn btn-ghost" :disabled="loading" @click="emit('cancel')">
        {{ cancelText }}
      </button>
      <button
        class="btn"
        :class="danger ? 'btn-danger' : 'btn-primary'"
        :disabled="loading"
        @click="emit('confirm')"
      >
        <span v-if="loading" class="inline-flex items-center gap-1.5">
          <span class="h-3 w-3 animate-spin rounded-full border border-current border-t-transparent" />
          处理中
        </span>
        <span v-else>{{ confirmText }}</span>
      </button>
    </template>
  </BaseModal>
</template>
