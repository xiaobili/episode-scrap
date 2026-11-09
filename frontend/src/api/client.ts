import axios from 'axios'

import type {
  DataSource,
  MatchResponse,
  MediaFile,
  OpenListInstance,
  Provider,
  RenamePreview,
  RollbackResult,
  ScanResponse,
  Settings,
  Show,
  ShowDetail,
  Task,
  TaskDetail,
  TreeResponse,
} from '@/types'

const http = axios.create({ baseURL: '/api', timeout: 90000 })

http.interceptors.response.use(
  (response) => response,
  (error) => {
    const detail = error?.response?.data?.detail
    let message = error.message || '请求失败'
    if (typeof detail === 'string') {
      message = detail
    } else if (Array.isArray(detail)) {
      message = detail.map((item) => item.msg ?? String(item)).join('；')
    }
    return Promise.reject(new Error(message))
  },
)

export const api = {
  getDataSources: () => http.get<DataSource[]>('/datasources').then((r) => r.data),

  getOpenListInstances: () =>
    http.get<OpenListInstance[]>('/datasources/openlist').then((r) => r.data),

  createOpenList: (payload: Record<string, unknown>) =>
    http.post<OpenListInstance>('/datasources/openlist', payload).then((r) => r.data),

  updateOpenList: (id: number, payload: Record<string, unknown>) =>
    http.put<OpenListInstance>(`/datasources/openlist/${id}`, payload).then((r) => r.data),

  deleteOpenList: (id: number) =>
    http.delete(`/datasources/openlist/${id}`).then((r) => r.data),

  testOpenList: (id: number) =>
    http
      .post<{ ok: boolean; message: string }>(`/datasources/openlist/${id}/test`)
      .then((r) => r.data),

  getOpenListTree: (id: number, path: string) =>
    http
      .get<TreeResponse>(`/datasources/openlist/${id}/tree`, { params: { path } })
      .then((r) => r.data),

  getLocalTree: (path: string) =>
    http.get<TreeResponse>('/directories/tree', { params: { path } }).then((r) => r.data),

  scan: (payload: {
    source_type: string
    source_ref: string
    openlist_id?: number | null
    recursive: boolean
  }) => http.post<ScanResponse>('/scan', payload).then((r) => r.data),

  getFiles: () => http.get<MediaFile[]>('/files').then((r) => r.data),

  parse: (payload: { file_ids?: number[]; all_files?: boolean }) =>
    http.post<MediaFile[]>('/parse', payload).then((r) => r.data),

  updateParse: (id: number, payload: Record<string, unknown>) =>
    http.put<MediaFile>(`/parse/${id}`, payload).then((r) => r.data),

  getProviders: () => http.get<Provider[]>('/providers').then((r) => r.data),

  search: (params: { query: string; provider: string; year?: number | null }) =>
    http.get<Show[]>('/search', { params }).then((r) => r.data),

  getShow: (provider: string, id: string, season?: number | null) =>
    http
      .get<ShowDetail>(`/shows/${provider}/${id}`, {
        params: season === null || season === undefined ? {} : { season },
      })
      .then((r) => r.data),

  match: (payload: {
    file_ids: number[]
    provider: string
    show_id: string
    season?: number | null
  }) => http.post<MatchResponse>('/match', payload).then((r) => r.data),

  previewRename: (payload: { file_ids?: number[]; template?: string }) =>
    http.post<RenamePreview>('/rename/preview', payload).then((r) => r.data),

  executeRename: (payload: {
    file_ids?: number[]
    template?: string
    write_nfo: boolean
    download_posters: boolean
    conflict_policy: 'skip' | 'suffix'
  }) =>
    http
      .post<{ task_id: string; total: number }>('/rename/execute', payload)
      .then((r) => r.data),

  rollback: (taskId?: string | null) =>
    http
      .post<RollbackResult>('/rename/rollback', { task_id: taskId ?? null })
      .then((r) => r.data),

  getTasks: (params?: { type?: string; status?: string }) =>
    http.get<Task[]>('/tasks', { params }).then((r) => r.data),

  getTask: (id: string) => http.get<TaskDetail>(`/tasks/${id}`).then((r) => r.data),

  retryTask: (id: string) => http.post<Task>(`/tasks/${id}/retry`).then((r) => r.data),

  getSettings: () => http.get<Settings>('/settings').then((r) => r.data),

  updateSettings: (payload: Record<string, unknown>) =>
    http.put<Settings>('/settings', payload).then((r) => r.data),
}

export function wsUrl(taskId: string): string {
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
  return `${protocol}://${window.location.host}/ws/tasks/${taskId}`
}
