<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    name: string
    size?: number
    stroke?: number
    spin?: boolean
  }>(),
  { size: 16, stroke: 1.7, spin: false },
)

const paths: Record<string, string[]> = {
  scan: ['M11 4a7 7 0 1 0 0 14 7 7 0 1 0 0-14', 'M21 21l-4.3-4.3'],
  parse: ['M4 6h16', 'M4 12h10', 'M4 18h13'],
  scrape: ['M12 3l2.4 5.2 5.6.7-4.1 3.9 1.1 5.6L12 15.8 7 18.4l1.1-5.6L4 8.9l5.6-.7z'],
  rename: ['M4 20h4l10-10-4-4L4 16z', 'M13.5 6.5l4 4'],
  tasks: ['M12 3a9 9 0 1 0 0 18 9 9 0 1 0 0-18', 'M12 8v4l3 2'],
  settings: [
    'M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6',
    'M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.9.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.9 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.9l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.9.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.9-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.9V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z',
  ],
  search: ['M11 4a7 7 0 1 0 0 14 7 7 0 1 0 0-14', 'M21 21l-4.3-4.3'],
  film: ['M3 4h18v16H3z', 'M3 9h18', 'M3 15h18', 'M8 4v5', 'M16 4v5', 'M8 15v5', 'M16 15v5'],
  folder: ['M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z'],
  cloud: ['M7 18a4 4 0 0 1-.7-7.9A5.5 5.5 0 0 1 17 8.5a3.5 3.5 0 0 1 .5 7z'],
  file: ['M5 3h9l5 5v13H5z', 'M14 3v5h5'],
  sun: [
    'M12 7a5 5 0 1 0 0 10 5 5 0 1 0 0-10',
    'M12 1v2',
    'M12 21v2',
    'M4.2 4.2l1.4 1.4',
    'M18.4 18.4l1.4 1.4',
    'M1 12h2',
    'M21 12h2',
    'M4.2 19.8l1.4-1.4',
    'M18.4 5.6l1.4-1.4',
  ],
  moon: ['M21 12.8A8.5 8.5 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z'],
  'chevron-right': ['M9 6l6 6-6 6'],
  'chevron-left': ['M15 6l-6 6 6 6'],
  'chevron-down': ['M6 9l6 6 6-6'],
  'arrow-right': ['M4 12h16', 'M14 6l6 6-6 6'],
  'arrow-left': ['M20 12H4', 'M10 6l-6 6 6 6'],
  check: ['M4 12l5 5L20 6'],
  'check-circle': ['M12 2a10 10 0 1 0 0 20 10 10 0 1 0 0-20', 'M8 12l3 3 5-6'],
  x: ['M6 6l12 12', 'M18 6L6 18'],
  plus: ['M12 5v14', 'M5 12h14'],
  refresh: ['M20 11a8 8 0 1 0-2 6', 'M20 5v6h-6'],
  undo: ['M9 14l-5-5 5-5', 'M4 9h10a6 6 0 0 1 0 12h-3'],
  alert: ['M12 3l9 16H3z', 'M12 9v5', 'M12 17h.01'],
  play: ['M7 4l13 8-13 8z'],
  database: ['M4 6c0-2 16-2 16 0s-16 2-16 0', 'M4 6v12c0 2 16 2 16 0V6', 'M4 12c0 2 16 2 16 0'],
  server: ['M4 4h16v6H4z', 'M4 14h16v6H4z', 'M8 7h.01', 'M8 17h.01'],
  sparkles: ['M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z'],
  external: ['M14 4h6v6', 'M20 4l-9 9', 'M18 14v5H5V6h5'],
  trash: ['M4 7h16', 'M9 7V4h6v3', 'M6 7l1 13h10l1-13', 'M10 11v5', 'M14 11v5'],
  copy: ['M9 9h11v11H9z', 'M5 15V4h11'],
  clock: ['M12 3a9 9 0 1 0 0 18 9 9 0 1 0 0-18', 'M12 7v5l3 2'],
  'panel-left': ['M4 4h16v16H4z', 'M10 4v16'],
  filter: ['M3 5h18l-7 8v6l-4 2v-8z'],
  loader: [
    'M12 2v4',
    'M12 18v4',
    'M4.9 4.9l2.8 2.8',
    'M16.3 16.3l2.8 2.8',
    'M2 12h4',
    'M18 12h4',
    'M4.9 19.1l2.8-2.8',
    'M16.3 7.7l2.8-2.8',
  ],
}

const iconPaths = paths[props.name] ?? paths.file
</script>

<template>
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    :stroke-width="stroke"
    stroke-linecap="round"
    stroke-linejoin="round"
    :class="spin ? 'animate-spin' : ''"
    aria-hidden="true"
  >
    <path v-for="(d, index) in iconPaths" :key="index" :d="d" />
  </svg>
</template>
