<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppIcon from '@/components/AppIcon.vue'
import { useWorkflowStore } from '@/stores/workflow'

const store = useWorkflowStore()
const route = useRoute()
const router = useRouter()

const steps = computed(() => [
  { name: 'scan', label: '扫描', count: store.stepCounts.scan, disabled: false },
  {
    name: 'parse',
    label: '解析',
    count: store.stepCounts.parse,
    disabled: store.stepCounts.scan === 0,
  },
  {
    name: 'scrape',
    label: '刮削',
    count: store.stepCounts.scrape,
    disabled: store.stepCounts.parse === 0,
  },
  {
    name: 'rename',
    label: '重命名',
    count: store.stepCounts.rename,
    disabled: store.stepCounts.parse === 0,
  },
])

const activeIndex = computed(() => {
  const index = steps.value.findIndex((step) => step.name === route.name)
  return index < 0 ? 0 : index
})

const activeStep = computed(() => steps.value[activeIndex.value])

function go(name: string, disabled: boolean) {
  if (disabled) return
  if (route.name !== name) router.push({ name })
}
</script>

<template>
  <nav class="flex items-center gap-1">
    <div class="hidden items-center gap-1 lg:flex">
      <template v-for="(step, index) in steps" :key="step.name">
        <span v-if="index > 0" class="mx-1 h-px w-4 bg-[var(--border-strong)]" />
        <button
          class="flex h-8 items-center gap-2 rounded-md px-2.5 text-[13px] transition"
          :class="[
            index === activeIndex
              ? 'bg-[var(--accent-soft)] text-ink'
              : 'text-muted hover:bg-[var(--bg-elevated)] hover:text-ink',
            step.disabled ? 'cursor-not-allowed opacity-40 hover:bg-transparent' : '',
          ]"
          :title="step.disabled ? '请先完成上一步' : `前往${step.label}`"
          @click="go(step.name, step.disabled)"
        >
          <span
            class="grid h-5 w-5 flex-none place-items-center rounded-full border font-mono text-[10.5px]"
            :class="
              index < activeIndex
                ? 'border-accent bg-accent font-semibold text-[#06231f]'
                : index === activeIndex
                  ? 'border-accent text-accent shadow-[0_0_0_3px_var(--accent-soft)]'
                  : 'border-[var(--border-strong)] text-muted'
            "
          >
            <AppIcon v-if="index < activeIndex" name="check" :size="11" :stroke="2.6" />
            <template v-else>{{ index + 1 }}</template>
          </span>
          <span>{{ step.label }}</span>
          <span v-if="step.count > 0" class="font-mono text-[10.5px] text-faint">
            {{ step.count }}
          </span>
        </button>
      </template>
    </div>

    <div class="flex items-center gap-2 text-[13px] lg:hidden">
      <span class="font-mono text-xs text-muted">{{ activeIndex + 1 }}/4</span>
      <span class="font-medium text-ink">{{ activeStep.label }}</span>
    </div>
  </nav>
</template>
