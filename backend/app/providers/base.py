from abc import ABC, abstractmethod
from dataclasses import dataclass, field


class ProviderError(Exception):
    pass


class ProviderNotConfigured(ProviderError):
    pass


@dataclass
class Show:
    provider: str
    id: str
    title: str
    original_title: str | None = None
    year: int | None = None
    overview: str | None = None
    poster_url: str | None = None
    rating: float | None = None
    seasons_count: int = 0


@dataclass
class EpisodeInfo:
    episode: int
    title: str | None = None
    overview: str | None = None
    air_date: str | None = None
    still_url: str | None = None


@dataclass
class SeasonInfo:
    season: int
    name: str
    episode_count: int
    episodes: list[EpisodeInfo] = field(default_factory=list)


@dataclass
class ShowDetail(Show):
    seasons: list[SeasonInfo] = field(default_factory=list)


class BaseProvider(ABC):
    name: str

    @abstractmethod
    async def search(self, query: str, year: int | None = None) -> list[Show]: ...

    @abstractmethod
    async def get_show(self, show_id: str, season: int | None = None) -> ShowDetail: ...

    @abstractmethod
    async def get_season(self, show_id: str, season: int) -> SeasonInfo: ...
