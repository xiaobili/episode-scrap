import { computed, ref, watch, type Ref } from 'vue'

import type { FolderGroup } from './useFolderGroups'

/**
 * 管理「文件夹组 → 季文件夹组」两级折叠状态。
 * 默认规则：某级只有一个子组且父级已展开时自动展开；数据或筛选结构变化时重建。
 */
export function useGroupExpansion<T>(groups: Ref<FolderGroup<T>[]>) {
  const openShows = ref<Set<string>>(new Set())
  const openSeasons = ref<Set<string>>(new Set())

  const signature = computed(() =>
    groups.value
      .map(
        (group) =>
          `${group.key}:${group.items.length}:${group.seasons
            .map((season) => `${season.key}:${season.items.length}`)
            .join(',')}`,
      )
      .join('|'),
  )

  watch(
    signature,
    () => {
      const nextShows = new Set<string>()
      const nextSeasons = new Set<string>()
      if (groups.value.length === 1) {
        const group = groups.value[0]
        nextShows.add(group.key)
        if (group.seasons.length === 1) nextSeasons.add(group.seasons[0].key)
      }
      openShows.value = nextShows
      openSeasons.value = nextSeasons
    },
    { immediate: true },
  )

  function isShowOpen(key: string): boolean {
    return openShows.value.has(key)
  }

  function isSeasonOpen(key: string): boolean {
    return openSeasons.value.has(key)
  }

  function toggleShow(key: string) {
    const next = new Set(openShows.value)
    if (next.has(key)) next.delete(key)
    else next.add(key)
    openShows.value = next
  }

  function toggleSeason(seasonKey: string) {
    const next = new Set(openSeasons.value)
    if (next.has(seasonKey)) next.delete(seasonKey)
    else next.add(seasonKey)
    openSeasons.value = next
  }

  function expandPath(showKey: string, seasonKey: string) {
    if (!openShows.value.has(showKey)) {
      openShows.value = new Set([...openShows.value, showKey])
    }
    if (!openSeasons.value.has(seasonKey)) {
      openSeasons.value = new Set([...openSeasons.value, seasonKey])
    }
  }

  return { openShows, openSeasons, isShowOpen, isSeasonOpen, toggleShow, toggleSeason, expandPath }
}
