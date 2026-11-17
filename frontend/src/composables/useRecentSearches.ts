import { ref, type Ref } from 'vue'

const KEY = 'episode-scrap-recent-searches'

export function useRecentSearches(max = 4): { items: Ref<string[]>; push: (query: string) => void } {
  const items = ref<string[]>([])
  try {
    const raw = localStorage.getItem(KEY)
    const parsed = raw ? (JSON.parse(raw) as unknown) : []
    if (Array.isArray(parsed)) {
      items.value = parsed.filter((value): value is string => typeof value === 'string').slice(0, max)
    }
  } catch {
    items.value = []
  }

  const push = (query: string) => {
    const value = query.trim()
    if (!value) return
    items.value = [value, ...items.value.filter((item) => item !== value)].slice(0, max)
    try {
      localStorage.setItem(KEY, JSON.stringify(items.value))
    } catch {
      /* 存储不可用时仅保留内存中的最近搜索 */
    }
  }

  return { items, push }
}
