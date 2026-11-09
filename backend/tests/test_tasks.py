import asyncio
import os
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.db import engine
from app.main import app
from app.models import MediaFile, RenameHistory, ScrapeMatch, TaskItem, TaskRecord


def add_media(tmp_path: Path, name: str, episode: int, with_match: bool = True) -> int:
    path = tmp_path / name
    path.write_bytes(b"video")
    with Session(engine) as session:
        media = MediaFile(
            source_type="local",
            source_ref=str(path),
            original_name=name,
            is_video=True,
            parsed_title="Show",
            parsed_year=2020,
            parsed_season=1,
            parsed_episode=episode,
            confidence=90,
            status="matched" if with_match else "parsed",
        )
        session.add(media)
        session.commit()
        session.refresh(media)
        if with_match:
            session.add(
                ScrapeMatch(
                    file_id=media.id,
                    provider="tmdb",
                    show_id="1",
                    show_title="Show",
                    show_year=2020,
                    season=1,
                    episode=episode,
                    episode_title=f"第 {episode} 集",
                    plot="简介",
                    air_date="2020-01-01",
                    rating=8.0,
                )
            )
            session.commit()
        return media.id


async def wait_for_task(client, task_id: str, timeout: float = 5.0) -> dict:
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        response = await client.get(f"/api/tasks/{task_id}")
        data = response.json()
        if data["status"] in ("completed", "failed"):
            return data
        await asyncio.sleep(0.05)
    raise AssertionError(f"任务未在 {timeout}s 内完成")


async def test_execute_rename_and_rollback(client, tmp_path):
    first = add_media(tmp_path, "Show.S01E01.mkv", 1)
    second = add_media(tmp_path, "Show.S01E02.mkv", 2)

    response = await client.post(
        "/api/rename/execute",
        json={
            "file_ids": [first, second],
            "template": "{title} - S{season:02d}E{episode:02d}",
            "write_nfo": True,
        },
    )
    assert response.status_code == 200, response.text
    task_id = response.json()["task_id"]
    assert response.json()["total"] == 2

    detail = await wait_for_task(client, task_id)
    assert detail["status"] == "completed"
    assert detail["done"] == 2
    assert detail["failed"] == 0
    assert (tmp_path / "Show - S01E01.mkv").exists()
    assert (tmp_path / "Show - S01E02.mkv").exists()
    assert (tmp_path / "Show - S01E01.nfo").exists()
    assert not (tmp_path / "Show.S01E01.mkv").exists()

    with Session(engine) as session:
        histories = session.exec(
            select(RenameHistory).where(RenameHistory.task_id == task_id)
        ).all()
        assert len(histories) == 2
        assert all(not h.rolled_back for h in histories)

    rollback = await client.post("/api/rename/rollback", json={"task_id": task_id})
    assert rollback.status_code == 200, rollback.text
    assert rollback.json()["restored"] == 2
    assert rollback.json()["failed"] == 0
    assert (tmp_path / "Show.S01E01.mkv").exists()
    assert not (tmp_path / "Show - S01E01.mkv").exists()

    with Session(engine) as session:
        histories = session.exec(
            select(RenameHistory).where(RenameHistory.task_id == task_id)
        ).all()
        assert all(h.rolled_back for h in histories)


async def test_execute_skips_conflict(client, tmp_path):
    media_id = add_media(tmp_path, "Show.S01E01.mkv", 1)
    (tmp_path / "Show - S01E01.mkv").write_bytes(b"existing")

    response = await client.post(
        "/api/rename/execute",
        json={
            "file_ids": [media_id],
            "template": "{title} - S{season:02d}E{episode:02d}",
            "write_nfo": False,
            "conflict_policy": "skip",
        },
    )
    assert response.status_code == 400
    assert (tmp_path / "Show.S01E01.mkv").exists()
    assert (tmp_path / "Show - S01E01.mkv").read_bytes() == b"existing"


async def test_execute_suffix_policy(client, tmp_path):
    media_id = add_media(tmp_path, "Show.S01E01.mkv", 1)
    (tmp_path / "Show - S01E01.mkv").write_bytes(b"existing")

    response = await client.post(
        "/api/rename/execute",
        json={
            "file_ids": [media_id],
            "template": "{title} - S{season:02d}E{episode:02d}",
            "write_nfo": False,
            "conflict_policy": "suffix",
        },
    )
    assert response.status_code == 200, response.text
    detail = await wait_for_task(client, response.json()["task_id"])
    assert detail["done"] == 1
    assert (tmp_path / "Show - S01E01 (1).mkv").exists()


async def test_nfo_failure_does_not_fail_rename(client, tmp_path, monkeypatch):
    media_id = add_media(tmp_path, "Show.S01E01.mkv", 1)

    async def broken_upload(self, *args, **kwargs):
        raise RuntimeError("upload failed")

    monkeypatch.setattr("app.datasources.local.LocalDataSource.upload", broken_upload)

    response = await client.post(
        "/api/rename/execute",
        json={
            "file_ids": [media_id],
            "template": "{title} - S{season:02d}E{episode:02d}",
            "write_nfo": True,
        },
    )
    assert response.status_code == 200, response.text
    task_id = response.json()["task_id"]
    detail = await wait_for_task(client, task_id)
    assert detail["done"] == 1
    assert detail["failed"] == 0
    assert (tmp_path / "Show - S01E01.mkv").exists()

    with Session(engine) as session:
        histories = session.exec(
            select(RenameHistory).where(RenameHistory.task_id == task_id)
        ).all()
        assert len(histories) == 1


async def test_rollback_reports_missing_file(client, tmp_path):
    first = add_media(tmp_path, "Show.S01E01.mkv", 1)
    second = add_media(tmp_path, "Show.S01E02.mkv", 2)
    response = await client.post(
        "/api/rename/execute",
        json={
            "file_ids": [first, second],
            "template": "{title} - S{season:02d}E{episode:02d}",
            "write_nfo": False,
        },
    )
    task_id = response.json()["task_id"]
    await wait_for_task(client, task_id)

    os.remove(tmp_path / "Show - S01E02.mkv")
    rollback = await client.post("/api/rename/rollback", json={"task_id": task_id})
    data = rollback.json()
    assert data["restored"] == 1
    assert data["failed"] == 1
    assert data["errors"]

    with Session(engine) as session:
        histories = session.exec(
            select(RenameHistory).where(RenameHistory.task_id == task_id)
        ).all()
        statuses = sorted(h.rolled_back for h in histories)
        assert statuses == [False, True]


def test_ws_sends_snapshot():
    task_id = uuid4().hex
    with Session(engine) as session:
        session.add(
            TaskRecord(
                id=task_id,
                type="rename",
                source_type="local",
                status="completed",
                total=1,
                done=1,
            )
        )
        session.commit()

    with TestClient(app) as test_client:
        with test_client.websocket_connect(f"/ws/tasks/{task_id}") as websocket:
            message = websocket.receive_json()
            assert message["task_id"] == task_id
            assert message["status"] == "completed"


async def test_retry_failed_items(client, tmp_path):
    media_id = add_media(tmp_path, "Show.S01E01.mkv", 1)
    failed_task_id = uuid4().hex
    with Session(engine) as session:
        session.add(
            TaskRecord(
                id=failed_task_id,
                type="rename",
                source_type="local",
                status="completed",
                total=1,
                done=0,
                failed=1,
            )
        )
        session.add(
            TaskItem(
                task_id=failed_task_id,
                file_id=media_id,
                name="Show.S01E01.mkv",
                new_name="Show - S01E01.mkv",
                status="failed",
                error="模拟失败",
            )
        )
        session.commit()

    response = await client.post(f"/api/tasks/{failed_task_id}/retry")
    assert response.status_code == 200, response.text
    new_id = response.json()["id"]
    assert response.json()["total"] == 1
    detail = await wait_for_task(client, new_id)
    assert detail["total"] == 1
