import { computed, ref, watch, type Ref } from 'vue'

interface PaginationOptions {
  pageSize?: number
}

export function usePagination<T>(source: Ref<T[]>, options: PaginationOptions = {}) {
  const page = ref(1)
  const pageSize = ref(options.pageSize ?? 20)
  const total = computed(() => source.value.length)
  const pageCount = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))
  const pageItems = computed(() => {
    const start = (page.value - 1) * pageSize.value
    return source.value.slice(start, start + pageSize.value)
  })
  const rangeStart = computed(() =>
    total.value === 0 ? 0 : (page.value - 1) * pageSize.value + 1,
  )
  const rangeEnd = computed(() => Math.min(page.value * pageSize.value, total.value))

  watch([total, pageSize], () => {
    if (page.value > pageCount.value) page.value = pageCount.value
    if (page.value < 1) page.value = 1
  })

  return { page, pageSize, total, pageCount, pageItems, rangeStart, rangeEnd }
}
