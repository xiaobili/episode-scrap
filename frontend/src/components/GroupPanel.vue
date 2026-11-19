<script setup lang="ts">
import AppIcon from '@/components/AppIcon.vue'
import type { GroupBadge } from '@/components/ui-types'

withDefaults(
  defineProps<{
    title: string
    level?: 'folder' | 'season'
    index?: number | string | null
    expanded: boolean
    selectable?: boolean
    checked?: boolean
    indeterminate?: boolean
    checkLabel?: string
    meta?: string[]
    badges?: GroupBadge[]
    path?: string | null
  }>(),
  {
    level: 'folder',
    index: null,
    selectable: false,
    checked: false,
    indeterminate: false,
    checkLabel: undefined,
    meta: () => [],
    badges: () => [],
    path: null,
  },
)

const emit = defineEmits<{
  toggle: []
  check: []
}>()
</script>

<template>
  <div
    class="group-bar"
    :class="[`lv-${level}`, { open: expanded }]"
    role="button"
    tabindex="0"
    :aria-expanded="expanded"
    :aria-label="`${expanded ? '折叠' : '展开'} ${title}`"
    :title="path || undefined"
    @click="emit('toggle')"
    @keydown.enter.prevent="emit('toggle')"
    @keydown.space.prevent="emit('toggle')"
  >
    <span v-if="index !== null && index !== undefined" class="g-index">{{ index }}</span>
    <span class="g-chev" aria-hidden="true">
      <AppIcon name="chevron-right" :size="12" />
    </span>
    <span v-if="level === 'season'" class="g-mark" aria-hidden="true" />

    <label v-if="selectable" class="g-check" @click.stop @keydown.stop>
      <input
        type="checkbox"
        :checked="checked"
        :indeterminate.prop="indeterminate"
        :aria-label="checkLabel ?? `选择 ${title}`"
        @change="emit('check')"
      />
    </label>

    <span class="g-title">{{ title }}</span>

    <span v-if="meta.length" class="g-meta">
      <span v-for="entry in meta" :key="entry">{{ entry }}</span>
    </span>

    <span v-if="badges.length" class="g-badges">
      <span
        v-for="badge in badges"
        :key="badge.label"
        class="tag"
        :class="`tag-${badge.tone ?? 'mute'}`"
      >
        {{ badge.label }}
      </span>
    </span>
  </div>
</template>
