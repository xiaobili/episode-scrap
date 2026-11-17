<script setup lang="ts">
import { computed, ref } from 'vue'

import type { Show } from '@/types'

const props = defineProps<{ show: Show; selected?: boolean }>()
const emit = defineEmits<{ select: [show: Show] }>()

const failed = ref(false)
const mark = computed(() => (props.show.title || '?').slice(0, 2).toUpperCase())
</script>

<template>
  <button
    type="button"
    class="show-card"
    :class="{ on: selected }"
    @click="emit('select', show)"
  >
    <span class="poster">
      <img
        v-if="show.poster_url && !failed"
        :src="show.poster_url"
        :alt="show.title"
        loading="lazy"
        @error="failed = true"
      />
      <span v-else class="poster-art">
        <span class="mark">{{ mark }}</span>
        <span class="code">{{ show.provider.toUpperCase() }}</span>
      </span>
    </span>

    <span class="show-info">
      <h4>{{ show.title }}</h4>
      <span class="en">{{ show.original_title || show.title }}</span>
      <span class="show-meta">
        <span v-if="show.rating" class="stars">★ {{ show.rating.toFixed(1) }}</span>
        <span v-if="show.year" class="tag tag-mute">{{ show.year }}</span>
        <span class="tag tag-mute">{{ show.seasons_count }} 季</span>
      </span>
    </span>
  </button>
</template>
