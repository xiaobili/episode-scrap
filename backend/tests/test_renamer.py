from xml.etree import ElementTree as ET

import pytest
from sqlmodel import Session

from app.core.nfo import generate_episode_nfo
from app.core.renamer import (
    TemplateError,
    build_context,
    render_filename,
    validate_template,
)
from app.db import engine
from app.models import MediaFile, ScrapeMatch


def make_media(**overrides):
    data = {
        "source_type": "local",
        "source_ref": "/tmp/library/Show/Season 01/old.mkv",
        "original_name": "Show.S01E03.1080p.mkv",
        "is_video": True,
        "parsed_title": "Breaking Bad",
        "parsed_year": 2008,
        "parsed_season": 1,
        "parsed_episode": 3,
        "parsed_resolution": "1080p",
        "parsed_codec": "x264",
        "parsed_release_group": "DEMAND",
        "confidence": 100,
        "status": "matched",
    }
    data.update(overrides)
    return MediaFile(**data)


def test_render_template():
    media = make_media()
    context = build_context(media, None)
    assert (
        render_filename(
            "{title} - S{season:02d}E{episode:02d} - {episode_title}", context, ".mkv"
        )
        == "Breaking Bad - S01E03.mkv"
    )


def test_render_handles_empty_episode_title():
    context = build_context(make_media(), None)
    assert (
        render_filename("{title} - S{season:02d}E{episode:02d} - {episode_title}", context, ".mkv")
        == "Breaking Bad - S01E03.mkv"
    )


def test_unknown_template_variable_rejected():
    with pytest.raises(TemplateError):
        validate_template("{title} {foo}")


def test_render_requires_season_and_episode():
    context = build_context(make_media(parsed_episode=None), None)
    with pytest.raises(TemplateError):
        render_filename("{title} - S{season:02d}E{episode:02d}", context, ".mkv")


def test_nfo_contains_fields():
    media = make_media()
    match = ScrapeMatch(
        file_id=1,
        provider="tmdb",
        show_id="1396",
        show_title="Breaking Bad",
        show_year=2008,
        season=1,
        episode=3,
        episode_title="...And the Bag's in the River",
        plot="剧情简介",
        air_date="2008-01-27",
        rating=8.9,
    )
    xml = generate_episode_nfo(media, match)
    root = ET.fromstring(xml)
    assert root.tag == "episodedetails"
    assert root.findtext("title") == "...And the Bag's in the River"
    assert root.findtext("showtitle") == "Breaking Bad"
    assert root.findtext("season") == "1"
    assert root.findtext("episode") == "3"
    assert root.findtext("plot") == "剧情简介"
    assert root.findtext("aired") == "2008-01-27"
    assert root.findtext("rating") == "8.9"


async def test_preview_ready_conflict_and_skipped(client, tmp_path):
    ready_dir = tmp_path / "ready"
    ready_dir.mkdir()
    conflict_dir = tmp_path / "conflict"
    conflict_dir.mkdir()
    ready_file = ready_dir / "old-ready.mkv"
    ready_file.write_bytes(b"r")
    conflict_file = conflict_dir / "old-conflict.mkv"
    conflict_file.write_bytes(b"c")
    (conflict_dir / "Breaking Bad - S01E02.mkv").write_bytes(b"existing")

    with Session(engine) as session:
        ready = make_media(
            source_ref=str(ready_file),
            original_name="old-ready.mkv",
            parsed_episode=2,
        )
        conflict = make_media(
            source_ref=str(conflict_file),
            original_name="old-conflict.mkv",
            parsed_episode=2,
            parsed_season=1,
        )
        skipped = make_media(
            source_ref=str(tmp_path / "missing.mkv"),
            original_name="missing.mkv",
            parsed_episode=None,
        )
        session.add(ready)
        session.add(conflict)
        session.add(skipped)
        session.commit()
        for media in (ready, conflict, skipped):
            session.refresh(media)
            session.add(
                ScrapeMatch(
                    file_id=media.id,
                    provider="tmdb",
                    show_id="1396",
                    show_title="Breaking Bad",
                    show_year=2008,
                    season=1,
                    episode=media.parsed_episode or 1,
                )
            )
        session.commit()
        ids = [ready.id, conflict.id, skipped.id]

    response = await client.post(
        "/api/rename/preview",
        json={
            "file_ids": ids,
            "template": "{title} - S{season:02d}E{episode:02d}",
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    statuses = {item["original_name"]: item["status"] for item in data["items"]}
    assert statuses["old-ready.mkv"] == "ready"
    assert statuses["old-conflict.mkv"] == "conflict"
    assert statuses["missing.mkv"] == "skipped"
    assert data["conflicts"] == 1
    assert data["skipped"] == 1
    assert data["ready"] == 1


async def test_preview_invalid_template(client):
    response = await client.post(
        "/api/rename/preview", json={"file_ids": [], "template": "{title} {nope}"}
    )
    assert response.status_code == 400
