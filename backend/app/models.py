from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class OpenListInstance(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    base_url: str
    username: str
    password_encrypted: str
    mount_path: str = "/"
    timeout: int = 30
    concurrency: int = 3
    created_at: datetime = Field(default_factory=utcnow)


class MediaFile(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    source_type: str = Field(index=True)
    source_ref: str = Field(index=True)
    scan_root: str | None = Field(default=None, index=True)
    openlist_id: int | None = Field(default=None, index=True)
    original_name: str
    size: int = 0
    modified_at: str | None = None
    is_video: bool = True
    scanned_at: datetime = Field(default_factory=utcnow)

    parsed_title: str | None = None
    parsed_year: int | None = None
    parsed_season: int | None = None
    parsed_episode: int | None = None
    parsed_episode_end: int | None = None
    parsed_episode_title: str | None = None
    parsed_resolution: str | None = None
    parsed_codec: str | None = None
    parsed_release_group: str | None = None
    confidence: int = 0

    status: str = "pending"  # pending / parsed / matched / renamed / error
    new_name: str | None = None


class ScrapeMatch(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    file_id: int = Field(foreign_key="mediafile.id", index=True, unique=True)
    provider: str
    show_id: str
    show_title: str
    show_year: int | None = None
    season: int
    episode: int
    episode_title: str | None = None
    plot: str | None = None
    air_date: str | None = None
    rating: float | None = None
    poster_url: str | None = None
    still_url: str | None = None
    matched_at: datetime = Field(default_factory=utcnow)


class RenameHistory(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    task_id: str = Field(index=True)
    file_id: int | None = Field(default=None, index=True)
    source_type: str
    openlist_id: int | None = None
    original_path: str
    new_path: str
    executed_at: datetime = Field(default_factory=utcnow)
    rolled_back: bool = False


class TaskRecord(SQLModel, table=True):
    id: str = Field(primary_key=True)
    type: str = "rename"
    source_type: str = "local"
    status: str = "pending"  # pending / running / completed / failed
    total: int = 0
    done: int = 0
    failed: int = 0
    template: str | None = None
    write_nfo: bool = True
    download_posters: bool = False
    write_strm: bool = False
    created_at: datetime = Field(default_factory=utcnow)
    finished_at: datetime | None = None
    error: str | None = None


class TaskItem(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    task_id: str = Field(index=True)
    file_id: int | None = Field(default=None, index=True)
    name: str
    new_name: str | None = None
    status: str = "pending"  # pending / success / failed / skipped
    error: str | None = None


class Setting(SQLModel, table=True):
    key: str = Field(primary_key=True)
    value: str = ""
