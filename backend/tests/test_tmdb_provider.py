import httpx
from sqlmodel import Session, select

from app.api import scrape as scrape_api
from app.db import engine
from app.models import MediaFile, ScrapeMatch, Setting
from app.providers.tmdb import TMDBProvider
from app.services.crypto import encrypt


def handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if path.endswith("/search/tv"):
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "id": 1396,
                        "name": "绝命毒师",
                        "original_name": "Breaking Bad",
                        "first_air_date": "2008-01-20",
                        "overview": "一位化学老师转行制毒。",
                        "poster_path": "/poster.jpg",
                        "vote_average": 8.923,
                        "number_of_seasons": 5,
                    }
                ]
            },
        )
    if path.endswith("/season/1"):
        return httpx.Response(
            200,
            json={
                "season_number": 1,
                "name": "第 1 季",
                "episodes": [
                    {
                        "episode_number": 1,
                        "name": "试播集",
                        "overview": "开始。",
                        "air_date": "2008-01-20",
                        "still_path": "/still1.jpg",
                    },
                    {
                        "episode_number": 2,
                        "name": "猫入袋中",
                        "overview": "第二集。",
                        "air_date": "2008-01-27",
                        "still_path": None,
                    },
                ],
            },
        )
    if path.endswith("/tv/1396"):
        return httpx.Response(
            200,
            json={
                "id": 1396,
                "name": "绝命毒师",
                "original_name": "Breaking Bad",
                "first_air_date": "2008-01-20",
                "overview": "一位化学老师转行制毒。",
                "poster_path": "/poster.jpg",
                "vote_average": 8.9,
                "number_of_seasons": 5,
                "seasons": [
                    {"season_number": 1, "name": "第 1 季", "episode_count": 7},
                    {"season_number": 2, "name": "第 2 季", "episode_count": 13},
                ],
            },
        )
    return httpx.Response(404, json={"status_message": "not found"})


async def test_tmdb_search_mapping():
    provider = TMDBProvider("key", transport=httpx.MockTransport(handler))
    shows = await provider.search("绝命毒师")
    assert len(shows) == 1
    show = shows[0]
    assert show.provider == "tmdb"
    assert show.id == "1396"
    assert show.title == "绝命毒师"
    assert show.year == 2008
    assert show.poster_url == "https://image.tmdb.org/t/p/w500/poster.jpg"
    assert show.rating == 8.9
    assert show.seasons_count == 5
    await provider.close()


async def test_tmdb_show_detail_with_season():
    provider = TMDBProvider("key", transport=httpx.MockTransport(handler))
    detail = await provider.get_show("1396", season=1)
    assert detail.title == "绝命毒师"
    assert [s.season for s in detail.seasons] == [1, 2]
    season = next(s for s in detail.seasons if s.season == 1)
    assert [e.episode for e in season.episodes] == [1, 2]
    assert season.episodes[0].title == "试播集"
    assert season.episodes[1].still_url is None
    await provider.close()


async def test_search_without_key_returns_400(client):
    with Session(engine) as session:
        row = session.get(Setting, "tmdb_api_key")
        if row:
            session.delete(row)
            session.commit()
    response = await client.get("/api/search", params={"query": "绝命毒师"})
    assert response.status_code == 400
    assert "未配置 TMDB API Key" in response.json()["detail"]


async def test_match_endpoint(client, monkeypatch):
    with Session(engine) as session:
        row = session.get(Setting, "tmdb_api_key")
        if row:
            row.value = encrypt("test-key")
        else:
            session.add(Setting(key="tmdb_api_key", value=encrypt("test-key")))
        media = MediaFile(
            source_type="local",
            source_ref="/tmp/library/Show.S01E02.mkv",
            original_name="Show.S01E02.mkv",
            is_video=True,
            parsed_title="绝命毒师",
            parsed_season=1,
            parsed_episode=2,
            confidence=90,
            status="parsed",
        )
        session.add(media)
        session.commit()
        session.refresh(media)
        media_id = media.id

    monkeypatch.setattr(
        scrape_api,
        "get_provider",
        lambda name, key: TMDBProvider("key", transport=httpx.MockTransport(handler)),
    )

    response = await client.post(
        "/api/match",
        json={"file_ids": [media_id], "provider": "tmdb", "show_id": "1396", "season": 1},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert len(data["matched"]) == 1
    assert data["matched"][0]["episode_title"] == "猫入袋中"

    with Session(engine) as session:
        match = session.exec(
            select(ScrapeMatch).where(ScrapeMatch.file_id == media_id)
        ).first()
        assert match is not None
        assert match.show_title == "绝命毒师"
        assert match.episode == 2
        updated = session.get(MediaFile, media_id)
        assert updated.status == "matched"


async def test_match_missing_episode(client, monkeypatch):
    with Session(engine) as session:
        media = MediaFile(
            source_type="local",
            source_ref="/tmp/library/Show.S01E99.mkv",
            original_name="Show.S01E99.mkv",
            is_video=True,
            parsed_title="绝命毒师",
            parsed_season=1,
            parsed_episode=99,
            confidence=90,
            status="parsed",
        )
        session.add(media)
        session.commit()
        session.refresh(media)
        media_id = media.id

    monkeypatch.setattr(
        scrape_api,
        "get_provider",
        lambda name, key: TMDBProvider("key", transport=httpx.MockTransport(handler)),
    )

    response = await client.post(
        "/api/match",
        json={"file_ids": [media_id], "provider": "tmdb", "show_id": "1396", "season": 1},
    )
    assert response.status_code == 200
    assert response.json()["unmatched"][0]["status"] == "unmatched"
