import httpx

from app.providers.base import (
    BaseProvider,
    EpisodeInfo,
    ProviderError,
    ProviderNotConfigured,
    SeasonInfo,
    Show,
    ShowDetail,
)

IMAGE_BASE = "https://image.tmdb.org/t/p/w500"


class TMDBProvider(BaseProvider):
    name = "tmdb"

    def __init__(
        self,
        api_key: str,
        language: str = "zh-CN",
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        if not api_key:
            raise ProviderNotConfigured("未配置 TMDB API Key")
        self.api_key = api_key
        self.language = language
        self._client = httpx.AsyncClient(
            base_url="https://api.themoviedb.org/3", timeout=15, transport=transport
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def _get(self, path: str, params: dict | None = None) -> dict:
        payload = {"api_key": self.api_key, "language": self.language}
        if params:
            payload.update(params)
        response = await self._client.get(path, params=payload)
        if response.status_code in (401, 403):
            raise ProviderNotConfigured("TMDB API Key 无效或无权限")
        if response.status_code == 404:
            raise ProviderError("TMDB 未找到对应资源")
        if response.status_code >= 400:
            raise ProviderError(f"TMDB 请求失败（{response.status_code}）")
        return response.json()

    @staticmethod
    def _image(path: str | None) -> str | None:
        return f"{IMAGE_BASE}{path}" if path else None

    def _show(self, data: dict) -> ShowDetail:
        date = data.get("first_air_date") or ""
        year = int(date[:4]) if date[:4].isdigit() else None
        rating = data.get("vote_average")
        return ShowDetail(
            provider=self.name,
            id=str(data.get("id", "")),
            title=data.get("name") or data.get("original_name") or "",
            original_title=data.get("original_name"),
            year=year,
            overview=data.get("overview"),
            poster_url=self._image(data.get("poster_path")),
            rating=round(float(rating), 1) if rating else None,
            seasons_count=int(data.get("number_of_seasons") or 0),
        )

    async def search(self, query: str, year: int | None = None) -> list[Show]:
        params: dict = {"query": query}
        if year:
            params["first_air_date_year"] = year
        data = await self._get("/search/tv", params)
        return [self._show(item) for item in data.get("results") or []]

    async def get_show(self, show_id: str, season: int | None = None) -> ShowDetail:
        data = await self._get(f"/tv/{show_id}")
        show = self._show(data)
        show.seasons = [
            SeasonInfo(
                season=int(item.get("season_number") or 0),
                name=item.get("name") or "",
                episode_count=int(item.get("episode_count") or 0),
            )
            for item in data.get("seasons") or []
        ]
        if season is not None:
            detail = await self.get_season(show_id, season)
            show.seasons = [s for s in show.seasons if s.season != season] + [detail]
            show.seasons.sort(key=lambda s: s.season)
        return show

    async def get_season(self, show_id: str, season: int) -> SeasonInfo:
        data = await self._get(f"/tv/{show_id}/season/{season}")
        episodes = [
            EpisodeInfo(
                episode=int(item.get("episode_number") or 0),
                title=item.get("name"),
                overview=item.get("overview"),
                air_date=item.get("air_date"),
                still_url=self._image(item.get("still_path")),
            )
            for item in data.get("episodes") or []
        ]
        return SeasonInfo(
            season=int(data.get("season_number") or season),
            name=data.get("name") or f"第 {season} 季",
            episode_count=len(episodes),
            episodes=episodes,
        )
