from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.core.matcher import find_episode
from app.db import get_session
from app.models import MediaFile, ScrapeMatch
from app.providers import get_provider
from app.providers.base import (
    ProviderError,
    ProviderNotConfigured,
    SeasonInfo,
    ShowDetail,
)
from app.schemas import (
    EpisodeOut,
    MatchItemOut,
    MatchRequest,
    MatchResponse,
    SeasonOut,
    ShowDetailOut,
    ShowOut,
)
from app.services.settings import get_tmdb_key, has_tmdb_key

router = APIRouter(tags=["scrape"])


def _show_out(show) -> ShowOut:
    return ShowOut(
        provider=show.provider,
        id=show.id,
        title=show.title,
        original_title=show.original_title,
        year=show.year,
        overview=show.overview,
        poster_url=show.poster_url,
        rating=show.rating,
        seasons_count=show.seasons_count,
    )


def _season_out(season: SeasonInfo) -> SeasonOut:
    return SeasonOut(
        season=season.season,
        name=season.name,
        episode_count=season.episode_count,
        episodes=[
            EpisodeOut(
                episode=e.episode,
                title=e.title,
                overview=e.overview,
                air_date=e.air_date,
                still_url=e.still_url,
            )
            for e in season.episodes
        ],
    )


def _detail_out(detail: ShowDetail) -> ShowDetailOut:
    return ShowDetailOut(
        **_show_out(detail).model_dump(),
        seasons=[_season_out(s) for s in detail.seasons],
    )


def _provider(session: Session, name: str):
    key = get_tmdb_key(session) if name == "tmdb" else ""
    if name == "tmdb" and not key:
        raise HTTPException(
            status_code=400, detail="未配置 TMDB API Key，请前往设置页配置"
        )
    try:
        return get_provider(name, key)
    except ProviderNotConfigured as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/providers")
def list_providers(session: Session = Depends(get_session)) -> list[dict]:
    return [
        {"name": "tmdb", "label": "TMDB", "configured": has_tmdb_key(session)},
    ]


@router.get("/api/search", response_model=list[ShowOut])
async def search_shows(
    query: str = Query(min_length=1),
    provider: str = "tmdb",
    year: int | None = None,
    session: Session = Depends(get_session),
) -> list[ShowOut]:
    client = _provider(session, provider)
    try:
        shows = await client.search(query, year)
        return [_show_out(show) for show in shows]
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    finally:
        await client.close()


@router.get("/api/shows/{provider}/{show_id}", response_model=ShowDetailOut)
async def get_show(
    provider: str,
    show_id: str,
    season: int | None = None,
    session: Session = Depends(get_session),
) -> ShowDetailOut:
    client = _provider(session, provider)
    try:
        return _detail_out(await client.get_show(show_id, season))
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    finally:
        await client.close()


@router.post("/api/match", response_model=MatchResponse)
async def match_files(
    payload: MatchRequest, session: Session = Depends(get_session)
) -> MatchResponse:
    files = session.exec(select(MediaFile).where(MediaFile.id.in_(payload.file_ids))).all()
    if not files:
        raise HTTPException(status_code=404, detail="未找到待匹配文件")

    client = _provider(session, payload.provider)
    matched: list[MatchItemOut] = []
    unmatched: list[MatchItemOut] = []
    season_cache: dict[int, SeasonInfo] = {}
    show_meta: ShowDetail | None = None

    try:
        for media in files:
            season_no = (
                media.parsed_season if media.parsed_season is not None else payload.season
            )
            episode_no = media.parsed_episode
            base = MatchItemOut(
                file_id=media.id or 0,
                name=media.original_name,
                season=season_no,
                episode=episode_no,
                status="unmatched",
            )
            if season_no is None or episode_no is None:
                base.message = "缺少季集信息"
                unmatched.append(base)
                continue

            try:
                if season_no not in season_cache:
                    show_meta = await client.get_show(payload.show_id, season_no)
                    season_info = next(
                        (s for s in show_meta.seasons if s.season == season_no), None
                    )
                    if season_info is None:
                        base.message = f"该剧不存在第 {season_no} 季"
                        unmatched.append(base)
                        continue
                    season_cache[season_no] = season_info
            except ProviderError as exc:
                base.message = str(exc)
                unmatched.append(base)
                continue

            episode = find_episode(season_cache[season_no], episode_no)
            if not episode:
                base.message = f"第 {season_no} 季没有第 {episode_no} 集"
                unmatched.append(base)
                continue

            show = show_meta
            if show is None:
                base.message = "读取剧集详情失败"
                unmatched.append(base)
                continue
            existing = session.exec(
                select(ScrapeMatch).where(ScrapeMatch.file_id == media.id)
            ).first()
            if not existing:
                existing = ScrapeMatch(
                    file_id=media.id or 0,
                    provider=payload.provider,
                    show_id=show.id,
                    show_title=show.title,
                    show_year=show.year,
                    season=season_no,
                    episode=episode_no,
                )
            existing.provider = payload.provider
            existing.show_id = show.id
            existing.show_title = show.title
            existing.show_year = show.year
            existing.season = season_no
            existing.episode = episode_no
            existing.episode_title = episode.title
            existing.plot = episode.overview
            existing.air_date = episode.air_date
            existing.rating = show.rating
            existing.poster_url = show.poster_url
            existing.still_url = episode.still_url
            session.add(existing)

            media.status = "matched"
            session.add(media)
            matched.append(
                base.model_copy(
                    update={
                        "status": "matched",
                        "episode_title": episode.title,
                    }
                )
            )
        session.commit()
    finally:
        await client.close()

    return MatchResponse(matched=matched, unmatched=unmatched)
