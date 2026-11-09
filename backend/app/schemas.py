from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models import MediaFile, TaskItem, TaskRecord

SourceType = Literal["local", "openlist"]


class ParsedOut(BaseModel):
    title: str | None = None
    year: int | None = None
    season: int | None = None
    episode: int | None = None
    episode_end: int | None = None
    episode_title: str | None = None
    resolution: str | None = None
    codec: str | None = None
    release_group: str | None = None
    raw: str
    confidence: int = 0


class MediaFileOut(BaseModel):
    id: int
    source_type: str
    source_ref: str
    openlist_id: int | None = None
    original_name: str
    size: int
    modified_at: str | None = None
    is_video: bool
    parsed: ParsedOut | None = None
    confidence: int = 0
    status: str
    new_name: str | None = None


def media_file_out(f: MediaFile) -> MediaFileOut:
    parsed = None
    if f.parsed_title or f.parsed_season is not None or f.parsed_episode is not None:
        parsed = ParsedOut(
            title=f.parsed_title,
            year=f.parsed_year,
            season=f.parsed_season,
            episode=f.parsed_episode,
            episode_end=f.parsed_episode_end,
            episode_title=f.parsed_episode_title,
            resolution=f.parsed_resolution,
            codec=f.parsed_codec,
            release_group=f.parsed_release_group,
            raw=f.original_name,
            confidence=f.confidence,
        )
    return MediaFileOut(
        id=f.id or 0,
        source_type=f.source_type,
        source_ref=f.source_ref,
        openlist_id=f.openlist_id,
        original_name=f.original_name,
        size=f.size,
        modified_at=f.modified_at,
        is_video=f.is_video,
        parsed=parsed,
        confidence=f.confidence,
        status=f.status,
        new_name=f.new_name,
    )


class ScanRequest(BaseModel):
    source_type: SourceType = "local"
    source_ref: str
    openlist_id: int | None = None
    recursive: bool = True


class ScanResponse(BaseModel):
    files: list[MediaFileOut]
    total: int
    video_count: int
    other_count: int
    elapsed_ms: int


class TreeEntry(BaseModel):
    name: str
    path: str
    is_dir: bool = True


class TreeResponse(BaseModel):
    path: str
    parent: str | None = None
    entries: list[TreeEntry]


class ParseRequest(BaseModel):
    file_ids: list[int] | None = None
    all_files: bool = False


class ParseUpdate(BaseModel):
    title: str | None = None
    year: int | None = None
    season: int | None = None
    episode: int | None = None
    episode_end: int | None = None
    episode_title: str | None = None
    resolution: str | None = None
    codec: str | None = None
    release_group: str | None = None


class OpenListCreate(BaseModel):
    name: str
    base_url: str
    username: str
    password: str
    timeout: int = 30
    concurrency: int = 3


class OpenListUpdate(BaseModel):
    name: str | None = None
    base_url: str | None = None
    username: str | None = None
    password: str | None = None
    timeout: int | None = None
    concurrency: int | None = None


class OpenListOut(BaseModel):
    id: int
    name: str
    base_url: str
    username: str
    timeout: int
    concurrency: int
    has_password: bool = True
    created_at: datetime


class DataSourceOut(BaseModel):
    type: str
    id: int | None = None
    name: str
    base_url: str | None = None
    username: str | None = None


class TestConnectionOut(BaseModel):
    ok: bool
    message: str


class ShowOut(BaseModel):
    provider: str
    id: str
    title: str
    original_title: str | None = None
    year: int | None = None
    overview: str | None = None
    poster_url: str | None = None
    rating: float | None = None
    seasons_count: int = 0


class EpisodeOut(BaseModel):
    episode: int
    title: str | None = None
    overview: str | None = None
    air_date: str | None = None
    still_url: str | None = None


class SeasonOut(BaseModel):
    season: int
    name: str
    episode_count: int
    episodes: list[EpisodeOut] = Field(default_factory=list)


class ShowDetailOut(ShowOut):
    seasons: list[SeasonOut] = Field(default_factory=list)


class MatchRequest(BaseModel):
    file_ids: list[int]
    provider: str = "tmdb"
    show_id: str
    season: int | None = None


class MatchItemOut(BaseModel):
    file_id: int
    name: str
    season: int | None = None
    episode: int | None = None
    episode_title: str | None = None
    status: Literal["matched", "unmatched"]
    message: str | None = None


class MatchResponse(BaseModel):
    matched: list[MatchItemOut]
    unmatched: list[MatchItemOut]


class RenamePreviewRequest(BaseModel):
    file_ids: list[int] | None = None
    template: str | None = None


class RenamePreviewItem(BaseModel):
    file_id: int
    original_name: str
    new_name: str | None = None
    status: Literal["ready", "conflict", "skipped", "error"]
    reason: str | None = None


class RenamePreviewOut(BaseModel):
    items: list[RenamePreviewItem]
    ready: int
    conflicts: int
    skipped: int
    total: int
    template: str


class RenameExecuteRequest(BaseModel):
    file_ids: list[int] | None = None
    template: str | None = None
    write_nfo: bool = True
    download_posters: bool = False
    write_strm: bool = False
    conflict_policy: Literal["skip", "suffix"] = "skip"


class RenameExecuteOut(BaseModel):
    task_id: str
    total: int


class RollbackRequest(BaseModel):
    task_id: str | None = None


class RollbackOut(BaseModel):
    task_id: str | None
    restored: int
    failed: int
    errors: list[str] = Field(default_factory=list)


class TaskItemOut(BaseModel):
    id: int
    file_id: int | None = None
    name: str
    new_name: str | None = None
    status: str
    error: str | None = None


def task_item_out(item: TaskItem) -> TaskItemOut:
    return TaskItemOut(
        id=item.id or 0,
        file_id=item.file_id,
        name=item.name,
        new_name=item.new_name,
        status=item.status,
        error=item.error,
    )


class TaskOut(BaseModel):
    id: str
    type: str
    source_type: str
    status: str
    total: int
    done: int
    failed: int
    template: str | None = None
    write_nfo: bool = True
    created_at: datetime
    finished_at: datetime | None = None
    error: str | None = None


def task_out(t: TaskRecord) -> TaskOut:
    return TaskOut(
        id=t.id,
        type=t.type,
        source_type=t.source_type,
        status=t.status,
        total=t.total,
        done=t.done,
        failed=t.failed,
        template=t.template,
        write_nfo=t.write_nfo,
        created_at=t.created_at,
        finished_at=t.finished_at,
        error=t.error,
    )


class TaskDetailOut(TaskOut):
    items: list[TaskItemOut] = Field(default_factory=list)


class StrmRule(BaseModel):
    source: str
    target_type: Literal["local", "openlist"] = "local"
    target_id: int | None = None
    target_dir: str


class SettingsOut(BaseModel):
    rename_template: str
    allowed_paths: list[str]
    has_tmdb_key: bool
    openlist_concurrency: int
    openlist_timeout: int
    openlist_retry: int
    strm_url_template: str
    strm_output_mode: str
    strm_target_dir: str
    strm_rules: list[StrmRule] = Field(default_factory=list)


class SettingsUpdate(BaseModel):
    rename_template: str | None = None
    allowed_paths: list[str] | None = None
    tmdb_api_key: str | None = None
    openlist_concurrency: int | None = None
    openlist_timeout: int | None = None
    openlist_retry: int | None = None
    strm_url_template: str | None = None
    strm_output_mode: Literal["alongside", "library", "mirror"] | None = None
    strm_target_dir: str | None = None
    strm_rules: list[StrmRule] | None = None
