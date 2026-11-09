import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { api } from '@/api/client'
import type {
  DataSource,
  MediaFile,
  Provider,
  RenamePreview,
  ScanResponse,
  Settings,
  ShowDetail,
} from '@/types'

export type SourceType = 'local' | 'openlist'

export interface ExecuteOptions {
  template?: string
  write_nfo: boolean
  download_posters: boolean
  write_strm: boolean
  conflict_policy: 'skip' | 'suffix'
}

export const useWorkflowStore = defineStore('workflow', () => {
  const files = ref<MediaFile[]>([])
  const datasources = ref<DataSource[]>([])
  const providers = ref<Provider[]>([])
  const settings = ref<Settings | null>(null)

  const selectedIds = ref<number[]>([])
  const sourceType = ref<SourceType>('local')
  const openlistId = ref<number | null>(null)
  const scanPath = ref('')
  const recursive = ref(true)

  const preview = ref<RenamePreview | null>(null)
  const currentShow = ref<ShowDetail | null>(null)

  const loading = ref(false)
  const scanning = ref(false)
  const parsing = ref(false)
  const matching = ref(false)
  const previewing = ref(false)
  const executing = ref(false)

  const videoFiles = computed(() => files.value.filter((file) => file.is_video))
  const parsedFiles = computed(() => videoFiles.value.filter((file) => file.parsed))
  const matchedFiles = computed(() =>
    videoFiles.value.filter((file) => file.status === 'matched' || file.status === 'renamed'),
  )

  const stepCounts = computed(() => ({
    scan: files.value.length,
    parse: parsedFiles.value.length,
    scrape: matchedFiles.value.length,
    rename: matchedFiles.value.filter((file) => file.status === 'matched').length,
  }))

  const selectedSet = computed(() => new Set(selectedIds.value))
  const selectedFiles = computed(() =>
    files.value.filter((file) => selectedSet.value.has(file.id)),
  )

  function mergeFiles(incoming: MediaFile[]) {
    const index = new Map(files.value.map((file) => [file.id, file]))
    for (const file of incoming) index.set(file.id, file)
    files.value = Array.from(index.values()).sort((a, b) => a.id - b.id)
  }

  function replaceFiles(incoming: MediaFile[]) {
    files.value = [...incoming].sort((a, b) => a.id - b.id)
  }

  function toggleSelected(id: number) {
    selectedIds.value = selectedSet.value.has(id)
      ? selectedIds.value.filter((item) => item !== id)
      : [...selectedIds.value, id]
  }

  function setSelected(ids: number[]) {
    selectedIds.value = [...ids]
  }

  function clearSelection() {
    selectedIds.value = []
  }

  function resetDownstream() {
    preview.value = null
    currentShow.value = null
  }

  async function init() {
    loading.value = true
    try {
      const [sources, providerList, settingsData, fileList] = await Promise.all([
        api.getDataSources(),
        api.getProviders(),
        api.getSettings(),
        api.getFiles(),
      ])
      datasources.value = sources
      providers.value = providerList
      settings.value = settingsData
      files.value = [...fileList].sort((a, b) => a.id - b.id)

      const local = sources.find((item) => item.type === 'local')
      if (local) sourceType.value = 'local'
      const firstOpenlist = sources.find((item) => item.type === 'openlist')
      if (!openlistId.value && firstOpenlist?.id) openlistId.value = firstOpenlist.id
      if (!scanPath.value && settingsData.allowed_paths.length > 0) {
        scanPath.value = settingsData.allowed_paths[0]
      }
    } finally {
      loading.value = false
    }
  }

  async function scan(): Promise<ScanResponse> {
    scanning.value = true
    try {
      const response = await api.scan({
        source_type: sourceType.value,
        source_ref: scanPath.value.trim(),
        openlist_id: sourceType.value === 'openlist' ? openlistId.value : null,
        recursive: recursive.value,
      })
      replaceFiles(response.files)
      clearSelection()
      resetDownstream()
      return response
    } finally {
      scanning.value = false
    }
  }

  async function parse(fileIds?: number[], allFiles = false) {
    parsing.value = true
    try {
      const updated = await api.parse({
        file_ids: fileIds && fileIds.length > 0 ? fileIds : undefined,
        all_files: allFiles,
      })
      mergeFiles(updated)
      preview.value = null
      return updated
    } finally {
      parsing.value = false
    }
  }

  async function updateParse(id: number, patch: Record<string, unknown>) {
    const updated = await api.updateParse(id, patch)
    mergeFiles([updated])
    preview.value = null
    return updated
  }

  async function refreshProviderState() {
    const [providerList, settingsData] = await Promise.all([api.getProviders(), api.getSettings()])
    providers.value = providerList
    settings.value = settingsData
  }

  async function previewRename(fileIds?: number[], template?: string) {
    previewing.value = true
    try {
      const result = await api.previewRename({
        file_ids: fileIds && fileIds.length > 0 ? fileIds : undefined,
        template,
      })
      preview.value = result
      return result
    } finally {
      previewing.value = false
    }
  }

  async function executeRename(fileIds: number[] | undefined, options: ExecuteOptions) {
    executing.value = true
    try {
      return await api.executeRename({
        file_ids: fileIds && fileIds.length > 0 ? fileIds : undefined,
        ...options,
      })
    } finally {
      executing.value = false
    }
  }

  async function rollback(taskId?: string | null) {
    return api.rollback(taskId ?? null)
  }

  async function refreshFiles() {
    const fileList = await api.getFiles()
    files.value = [...fileList].sort((a, b) => a.id - b.id)
  }

  return {
    files,
    datasources,
    providers,
    settings,
    selectedIds,
    sourceType,
    openlistId,
    scanPath,
    recursive,
    preview,
    currentShow,
    loading,
    scanning,
    parsing,
    matching,
    previewing,
    executing,
    videoFiles,
    parsedFiles,
    matchedFiles,
    stepCounts,
    selectedSet,
    selectedFiles,
    init,
    scan,
    parse,
    updateParse,
    refreshProviderState,
    previewRename,
    executeRename,
    rollback,
    refreshFiles,
    mergeFiles,
    replaceFiles,
    toggleSelected,
    setSelected,
    clearSelection,
    resetDownstream,
  }
})
