import asyncio
import os
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.db import engine
from app.main import app
from app.models import (
    MediaFile,
    OpenListInstance,
    RenameHistory,
    ScrapeMatch,
    TaskItem,
    TaskRecord,
)


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


class FakeOpenListSource:
    def __init__(self) -> None:
        self.uploads: list[tuple[str, str, str]] = []
        self.mkdirs: list[str] = []

    async def rename(self, path: str, new_name: str) -> str:
        parent = path.rsplit("/", 1)[0]
        return f"{parent}/{new_name}"

    async def exists(self, parent: str, name: str) -> bool:
        return False

    async def mkdir(self, path: str) -> None:
        self.mkdirs.append(path)

    def join(self, dir_path: str, name: str) -> str:
        return f"{dir_path.rstrip('/')}/{name}"

    async def upload(self, dir_path: str, content: bytes, filename: str) -> None:
        self.uploads.append((dir_path, content.decode("utf-8"), filename))


def patch_strm_options(
    monkeypatch,
    *,
    mode: str = "alongside",
    target_dir: str = "",
    template: str = "{base_url}/d/{path}",
    rules: list[dict] | None = None,
) -> None:
    monkeypatch.setattr(
        "app.services.task_manager.get_strm_options",
        lambda session: {
            "template": template,
            "mode": mode,
            "target_dir": target_dir,
            "rules": rules or [],
        },
    )


async def test_strm_written_alongside_local(client, tmp_path, monkeypatch):
    media_id = add_media(tmp_path, "Show.S01E01.mkv", 1)
    patch_strm_options(monkeypatch)

    response = await client.post(
        "/api/rename/execute",
        json={
            "file_ids": [media_id],
            "template": "{title} - S{season:02d}E{episode:02d}",
            "write_nfo": False,
            "write_strm": True,
        },
    )
    assert response.status_code == 200, response.text
    detail = await wait_for_task(client, response.json()["task_id"])
    assert detail["done"] == 1

    strm = tmp_path / "Show - S01E01.strm"
    assert strm.exists()
    assert strm.read_text(encoding="utf-8") == str(tmp_path / "Show - S01E01.mkv")


async def test_strm_written_to_library_dir(client, tmp_path, monkeypatch):
    media_id = add_media(tmp_path, "Show.S01E01.mkv", 1)
    library = tmp_path / "library"
    patch_strm_options(monkeypatch, mode="library", target_dir=str(library))

    response = await client.post(
        "/api/rename/execute",
        json={
            "file_ids": [media_id],
            "template": "{title} - S{season:02d}E{episode:02d}",
            "write_nfo": False,
            "write_strm": True,
        },
    )
    assert response.status_code == 200, response.text
    detail = await wait_for_task(client, response.json()["task_id"])
    assert detail["done"] == 1

    strm = library / "Show" / "Season 01" / "Show - S01E01.strm"
    assert strm.exists()
    assert strm.read_text(encoding="utf-8") == str(tmp_path / "Show - S01E01.mkv")


async def test_strm_written_alongside_openlist(client, tmp_path, monkeypatch):
    media_id = add_media(tmp_path, "Show.S01E01.mkv", 1)
    with Session(engine) as session:
        instance = OpenListInstance(
            name="cloud",
            base_url="https://fox.example.com",
            username="admin",
            password_encrypted="x",
        )
        session.add(instance)
        session.commit()
        session.refresh(instance)
        media = session.get(MediaFile, media_id)
        media.source_type = "openlist"
        media.openlist_id = instance.id
        media.source_ref = "/cloud/Show.S01E01.mkv"
        media.scan_root = "/cloud"
        session.add(media)
        session.commit()

    fake = FakeOpenListSource()
    monkeypatch.setattr(
        "app.services.rename_service.get_datasource", lambda *args, **kwargs: fake
    )
    monkeypatch.setattr(
        "app.services.task_manager.get_datasource", lambda *args, **kwargs: fake
    )
    patch_strm_options(monkeypatch)

    response = await client.post(
        "/api/rename/execute",
        json={
            "file_ids": [media_id],
            "template": "{title} - S{season:02d}E{episode:02d}",
            "write_nfo": False,
            "write_strm": True,
        },
    )
    assert response.status_code == 200, response.text
    detail = await wait_for_task(client, response.json()["task_id"])
    assert detail["done"] == 1

    assert fake.uploads == [
        (
            "/cloud",
            "https://fox.example.com/d/cloud/Show%20-%20S01E01.mkv",
            "Show - S01E01.strm",
        )
    ]


async def test_strm_rule_creates_show_folder_local(client, tmp_path, monkeypatch):
    show_dir = tmp_path / "美剧" / "大宋提刑官"
    show_dir.mkdir(parents=True)
    media_id = add_media(show_dir, "01.mkv", 1)
    library = tmp_path / "strm"
    patch_strm_options(
        monkeypatch,
        rules=[
            {
                "source": str(tmp_path / "美剧"),
                "target_type": "local",
                "target_id": None,
                "target_dir": str(library),
            }
        ],
    )

    response = await client.post(
        "/api/rename/execute",
        json={
            "file_ids": [media_id],
            "template": "{title} - S{season:02d}E{episode:02d}",
            "write_nfo": False,
            "write_strm": True,
        },
    )
    assert response.status_code == 200, response.text
    detail = await wait_for_task(client, response.json()["task_id"])
    assert detail["done"] == 1

    strm = library / "大宋提刑官" / "Show - S01E01.strm"
    assert strm.exists()
    assert strm.read_text(encoding="utf-8") == str(show_dir / "Show - S01E01.mkv")


async def test_strm_rule_creates_openlist_folders(client, tmp_path, monkeypatch):
    media_id = add_media(tmp_path, "Show.S01E01.mkv", 1)
    with Session(engine) as session:
        instance = OpenListInstance(
            name="cloud",
            base_url="https://fox.example.com",
            username="admin",
            password_encrypted="x",
        )
        session.add(instance)
        session.commit()
        session.refresh(instance)
        instance_id = instance.id
        media = session.get(MediaFile, media_id)
        media.source_type = "openlist"
        media.openlist_id = instance_id
        media.source_ref = "/cloud/美剧/大宋提刑官/Season 01/01.mkv"
        media.scan_root = "/cloud/美剧"
        session.add(media)
        session.commit()

    fake = FakeOpenListSource()
    monkeypatch.setattr(
        "app.services.rename_service.get_datasource", lambda *args, **kwargs: fake
    )
    monkeypatch.setattr(
        "app.services.task_manager.get_datasource", lambda *args, **kwargs: fake
    )
    patch_strm_options(
        monkeypatch,
        rules=[
            {
                "source": "/cloud/美剧",
                "target_type": "openlist",
                "target_id": instance_id,
                "target_dir": "/strm/美剧",
            }
        ],
    )

    response = await client.post(
        "/api/rename/execute",
        json={
            "file_ids": [media_id],
            "template": "{title} - S{season:02d}E{episode:02d}",
            "write_nfo": False,
            "write_strm": True,
        },
    )
    assert response.status_code == 200, response.text
    detail = await wait_for_task(client, response.json()["task_id"])
    assert detail["done"] == 1

    assert fake.mkdirs == [
        "/strm",
        "/strm/美剧",
        "/strm/美剧/大宋提刑官",
        "/strm/美剧/大宋提刑官/Season 01",
    ]
    assert fake.uploads[0][0] == "/strm/美剧/大宋提刑官/Season 01"
    assert fake.uploads[0][2] == "Show - S01E01.strm"
    assert fake.uploads[0][1].startswith("https://fox.example.com/d/cloud/")


async def test_posters_downloaded_for_openlist(client, tmp_path, monkeypatch):
    media_id = add_media(tmp_path, "Show.S01E01.mkv", 1)
    with Session(engine) as session:
        media = session.get(MediaFile, media_id)
        media.source_type = "openlist"
        media.openlist_id = 1
        media.source_ref = "/cloud/Show.S01E01.mkv"
        match = session.exec(
            select(ScrapeMatch).where(ScrapeMatch.file_id == media_id)
        ).first()
        match.still_url = "https://image.tmdb.org/t/p/w500/still.jpg"
        session.add(media)
        session.add(match)
        session.commit()

    fake = FakeOpenListSource()
    monkeypatch.setattr(
        "app.services.rename_service.get_datasource", lambda *args, **kwargs: fake
    )
    monkeypatch.setattr(
        "app.services.task_manager.get_datasource", lambda *args, **kwargs: fake
    )

    calls: list[tuple[str, str, str | None]] = []

    async def record(self, datasource, new_path, url, new_name):
        calls.append((new_path, url, new_name))

    monkeypatch.setattr("app.services.task_manager.TaskManager._download_thumb", record)

    response = await client.post(
        "/api/rename/execute",
        json={
            "file_ids": [media_id],
            "template": "{title} - S{season:02d}E{episode:02d}",
            "write_nfo": False,
            "download_posters": True,
        },
    )
    assert response.status_code == 200, response.text
    detail = await wait_for_task(client, response.json()["task_id"])
    assert detail["done"] == 1
    assert len(calls) == 1
    assert calls[0][1] == "https://image.tmdb.org/t/p/w500/still.jpg"


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
