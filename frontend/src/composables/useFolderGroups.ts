import { computed, type Ref } from 'vue'

import type { SourceType } from '@/types'

export interface SeasonFolderGroup<T> {
  key: string
  name: string
  path: string
  season: number | null
  direct: boolean
  items: T[]
  size: number | null
}

export interface FolderGroup<T> {
  key: string
  title: string
  path: string
  sourceType: SourceType
  openlistId: number | null
  unknown: boolean
  seasons: SeasonFolderGroup<T>[]
  items: T[]
  size: number | null
  seasonCount: number
  hasSeasons: boolean
}

interface FolderGroupOptions<T> {
  getPath: (item: T) => string | null
  getSourceType?: (item: T) => SourceType
  getOpenlistId?: (item: T) => number | null
  getSize?: (item: T) => number
  getName?: (item: T) => string
  unknownTitle?: string
}

const UNKNOWN_KEY = '__unknown_folder__'
const DIRECT_LABEL = '本目录'
const ROOT_LABEL = '根目录'
const SEASON_FOLDER = /^(?:season[\s._-]*|series[\s._-]*|s|第\s*)(\d{1,2})(?:\s*季)?$/i

const nameCollator = new Intl.Collator(undefined, { numeric: true, sensitivity: 'base' })

function normalizePath(path: string): string {
  const value = path.replace(/\\/g, '/').replace(/\/+/g, '/')
  if (value.length > 1 && value.endsWith('/')) return value.replace(/\/+$/, '')
  return value
}

function parentOf(path: string): string {
  if (!path || path === '/') return '/'
  const index = path.lastIndexOf('/')
  if (index <= 0) return '/'
  return path.slice(0, index)
}

function nameOf(path: string): string {
  if (!path || path === '/') return ''
  const index = path.lastIndexOf('/')
  return index >= 0 ? path.slice(index + 1) : path
}

/**
 * 季目录识别只看文件夹名，复用后端解析器的同一套语义：
 * Season 01 / S01 / Series 2 / 第1季 / 第 1 季。
 */
export function seasonNumberOf(folderName: string): number | null {
  const match = folderName.match(SEASON_FOLDER)
  return match ? Number(match[1]) : null
}

interface ResolvedFolder {
  showPath: string
  showTitle: string
  seasonPath: string | null
  seasonName: string | null
  season: number | null
}

function resolveFolder<T>(item: T, options: FolderGroupOptions<T>): ResolvedFolder | null {
  const raw = options.getPath(item)
  if (!raw) return null

  const dir = parentOf(normalizePath(raw))
  const dirName = nameOf(dir)
  const season = seasonNumberOf(dirName)

  if (season !== null) {
    const showPath = parentOf(dir)
    return {
      showPath,
      showTitle: nameOf(showPath) || ROOT_LABEL,
      seasonPath: dir,
      seasonName: dirName,
      season,
    }
  }

  return {
    showPath: dir,
    showTitle: dirName || ROOT_LABEL,
    seasonPath: null,
    seasonName: null,
    season: null,
  }
}

/**
 * 按媒体文件所在目录归并：一级是剧目录，若文件位于季目录内则季目录作为二级。
 * 分组只依赖路径与文件夹名，不读取解析结果。
 */
export function useFolderGroups<T>(source: Ref<T[]>, options: FolderGroupOptions<T>) {
  const groups = computed<FolderGroup<T>[]>(() => {
    const buckets = new Map<
      string,
      {
        title: string
        path: string
        sourceType: SourceType
        openlistId: number | null
        unknown: boolean
        seasons: Map<string, SeasonFolderGroup<T>>
        hasSeasons: boolean
      }
    >()

    for (const item of source.value) {
      const resolved = resolveFolder(item, options)
      const sourceType = options.getSourceType?.(item) ?? 'local'
      const openlistId = options.getOpenlistId?.(item) ?? null
      const groupKey = resolved
        ? `${sourceType}|${openlistId ?? ''}|${resolved.showPath}`
        : `${UNKNOWN_KEY}|${sourceType}|${openlistId ?? ''}`

      let bucket = buckets.get(groupKey)
      if (!bucket) {
        bucket = {
          title: resolved
            ? resolved.showTitle
            : (options.unknownTitle ?? '未知文件夹'),
          path: resolved?.showPath ?? '',
          sourceType,
          openlistId,
          unknown: resolved === null,
          seasons: new Map(),
          hasSeasons: false,
        }
        buckets.set(groupKey, bucket)
      }

      const seasonPath = resolved?.seasonPath ?? null
      const direct = seasonPath === null
      if (!direct) bucket.hasSeasons = true

      const seasonKey = `${groupKey}::${seasonPath ?? 'direct'}`
      let season = bucket.seasons.get(seasonKey)
      if (!season) {
        season = {
          key: seasonKey,
          name: direct ? DIRECT_LABEL : (resolved?.seasonName ?? DIRECT_LABEL),
          path: seasonPath ?? bucket.path,
          season: resolved?.season ?? null,
          direct,
          items: [],
          size: options.getSize ? 0 : null,
        }
        bucket.seasons.set(seasonKey, season)
      }
      season.items.push(item)
      if (season.size !== null && options.getSize) season.size += options.getSize(item)
    }

    const result: FolderGroup<T>[] = []
    for (const [key, bucket] of buckets) {
      const seasons = [...bucket.seasons.values()].sort((first, second) => {
        if (first.direct !== second.direct) return first.direct ? -1 : 1
        if (first.season === null && second.season === null) {
          return first.name.localeCompare(second.name, 'zh-CN')
        }
        if (first.season === null) return 1
        if (second.season === null) return -1
        if (first.season !== second.season) return first.season - second.season
        return first.name.localeCompare(second.name, 'zh-CN')
      })

      const nameOfItem = (item: T) => options.getName?.(item) ?? ''
      for (const season of seasons) {
        season.items.sort((first, second) =>
          nameCollator.compare(nameOfItem(first), nameOfItem(second)),
        )
      }

      const items = seasons.flatMap((season) => season.items)
      const seasonCount = seasons.filter((season) => !season.direct).length

      result.push({
        key,
        title: bucket.title,
        path: bucket.path,
        sourceType: bucket.sourceType,
        openlistId: bucket.openlistId,
        unknown: bucket.unknown,
        seasons,
        items,
        size: options.getSize
          ? seasons.reduce((sum, season) => sum + (season.size ?? 0), 0)
          : null,
        seasonCount,
        hasSeasons: bucket.hasSeasons,
      })
    }

    result.sort((first, second) => {
      if (first.unknown !== second.unknown) return first.unknown ? 1 : -1
      const byName = first.title.localeCompare(second.title, 'zh-CN')
      if (byName !== 0) return byName
      return first.path.localeCompare(second.path, 'zh-CN')
    })

    return result
  })

  return { groups }
}
