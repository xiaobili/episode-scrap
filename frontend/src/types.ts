export type SourceType = 'local' | 'openlist'

export interface Parsed {
  title: string | null
  year: number | null
  season: number | null
  episode: number | null
  episode_end: number | null
  episode_title: string | null
  resolution: string | null
  codec: string | null
  release_group: string | null
  raw: string
  confidence: number
}

export interface MediaFile {
  id: number
  source_type: SourceType
  source_ref: string
  scan_root?: string | null
  openlist_id: number | null
  original_name: string
  size: number
  modified_at: string | null
  is_video: boolean
  parsed: Parsed | null
  confidence: number
  status: string
  new_name: string | null
}

export interface DataSource {
  type: 'local' | 'openlist'
  id: number | null
  name: string
  base_url: string | null
  username: string | null
}

export interface OpenListInstance {
  id: number
  name: string
  base_url: string
  username: string
  timeout: number
  concurrency: number
  has_password: boolean
  created_at: string
}

export interface TreeEntry {
  name: string
  path: string
  is_dir: boolean
}

export interface TreeResponse {
  path: string
  parent: string | null
  entries: TreeEntry[]
}

export interface ScanResponse {
  files: MediaFile[]
  total: number
  video_count: number
  other_count: number
  elapsed_ms: number
}

export interface Show {
  provider: string
  id: string
  title: string
  original_title: string | null
  year: number | null
  overview: string | null
  poster_url: string | null
  rating: number | null
  seasons_count: number
}

export interface Episode {
  episode: number
  title: string | null
  overview: string | null
  air_date: string | null
  still_url: string | null
}

export interface Season {
  season: number
  name: string
  episode_count: number
  episodes: Episode[]
}

export interface ShowDetail extends Show {
  seasons: Season[]
}

export interface MatchItem {
  file_id: number
  name: string
  season: number | null
  episode: number | null
  episode_title: string | null
  status: 'matched' | 'unmatched'
  message: string | null
}

export interface MatchResponse {
  matched: MatchItem[]
  unmatched: MatchItem[]
}

export interface PreviewItem {
  file_id: number
  original_name: string
  new_name: string | null
  status: 'ready' | 'conflict' | 'skipped' | 'error'
  reason: string | null
}

export interface RenamePreview {
  items: PreviewItem[]
  ready: number
  conflicts: number
  skipped: number
  total: number
  template: string
}

export interface Task {
  id: string
  type: string
  source_type: string
  status: string
  total: number
  done: number
  failed: number
  template: string | null
  write_nfo: boolean
  created_at: string
  finished_at: string | null
  error: string | null
}

export interface TaskItem {
  id: number
  file_id: number | null
  name: string
  new_name: string | null
  status: string
  error: string | null
}

export interface TaskDetail extends Task {
  items: TaskItem[]
}

export interface StrmRule {
  source: string
  target_type: 'local' | 'openlist'
  target_id: number | null
  target_dir: string
}

export interface Settings {
  rename_template: string
  allowed_paths: string[]
  has_tmdb_key: boolean
  openlist_concurrency: number
  openlist_timeout: number
  openlist_retry: number
  strm_url_template: string
  strm_output_mode: 'alongside' | 'library' | 'mirror'
  strm_target_dir: string
  strm_rules: StrmRule[]
  jellyfin_url: string
  has_jellyfin_key: boolean
}

export interface RollbackResult {
  task_id: string | null
  restored: number
  failed: number
  errors: string[]
}

export interface Provider {
  name: string
  label: string
  configured: boolean
}

export interface JellyfinLibrary {
  id: string
  name: string
  collection_type: string | null
}

export interface JellyfinRefreshResult {
  library_id: string
  ok: boolean
  error: string | null
}
