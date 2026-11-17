<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ value: number }>()

const clamped = computed(() => Math.min(100, Math.max(0, props.value)))
const offset = computed(() => 226.2 * (1 - clamped.value / 100))
const color = computed(() =>
  clamped.value >= 85 ? 'var(--green)' : clamped.value >= 60 ? 'var(--amber)' : 'var(--red)',
)
const label = computed(() =>
  clamped.value >= 85 ? '高置信度' : clamped.value >= 60 ? '中置信度' : '低置信度',
)
</script>

<template>
  <aside class="conf-card">
    <div class="gauge-wrap">
      <svg class="gauge" width="88" height="88" viewBox="0 0 88 88" aria-hidden="true">
        <circle class="track" cx="44" cy="44" r="36" />
        <circle
          class="val"
          cx="44"
          cy="44"
          r="36"
          stroke-dasharray="226.2"
          :stroke-dashoffset="offset"
          :stroke="color"
        />
      </svg>
      <div class="gauge-num"><b>{{ clamped }}</b><span>%</span></div>
    </div>
    <div class="conf-label">{{ label }}</div>
    <div class="conf-sub">CONFIDENCE</div>
    <div class="conf-scale">
      <div><span><i style="background: var(--green)" /> HIGH ≥ 85</span></div>
      <div><span><i style="background: var(--amber)" /> MID 60–84</span></div>
      <div><span><i style="background: var(--red)" /> LOW &lt; 60</span></div>
    </div>
  </aside>
</template>
