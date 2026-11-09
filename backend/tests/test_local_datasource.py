from pathlib import Path

import pytest
from sqlmodel import Session, select

from app.datasources.local import LocalDataSource
from app.db import engine
from app.models import MediaFile


def make_show(tmp_path: Path) -> Path:
    folder = tmp_path / "Show" / "Season 01"
    folder.mkdir(parents=True)
    (folder / "Show.S01E01.1080p.mkv").write_bytes(b"video-1")
    (folder / "Show.S01E02.1080p.mkv").write_bytes(b"video-2")
    (tmp_path / "Show" / "notes.txt").write_text("hello")
    return tmp_path / "Show"


async def test_scan_filters_and_persists(client, tmp_path):
    root = make_show(tmp_path)
    response = await client.post(
        "/api/scan",
        json={"source_type": "local", "source_ref": str(root), "recursive": True},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["total"] == 3
    assert data["video_count"] == 2
    assert data["other_count"] == 1
    assert all(f["source_type"] == "local" for f in data["files"])
    assert {f["is_video"] for f in data["files"]} == {True, False}


async def test_scan_rejects_outside_whitelist(client, tmp_path):
    response = await client.post(
        "/api/scan", json={"source_type": "local", "source_ref": "/etc"}
    )
    assert response.status_code == 403


async def test_scan_rejects_traversal(client, tmp_path):
    escaping = f"{tmp_path}/../../../../etc"
    response = await client.post(
        "/api/scan", json={"source_type": "local", "source_ref": escaping}
    )
    assert response.status_code == 403


async def test_rescan_does_not_duplicate(client, tmp_path):
    root = make_show(tmp_path)
    payload = {"source_type": "local", "source_ref": str(root), "recursive": True}
    first = await client.post("/api/scan", json=payload)
    second = await client.post("/api/scan", json=payload)
    assert first.json()["total"] == second.json()["total"] == 3
    with Session(engine) as session:
        rows = session.exec(select(MediaFile).where(MediaFile.scan_root == str(root))).all()
    assert len(rows) == 3


async def test_local_rename_and_conflict(tmp_path):
    source = tmp_path / "a.mkv"
    source.write_bytes(b"a")
    target = tmp_path / "b.mkv"
    target.write_bytes(b"b")

    datasource = LocalDataSource()
    with pytest.raises(FileExistsError):
        await datasource.rename(str(source), "b.mkv")

    new_path = await datasource.rename(str(target), "c.mkv")
    assert Path(new_path).name == "c.mkv"
    assert Path(new_path).exists()


async def test_directory_tree(client, tmp_path):
    root = tmp_path / "library"
    (root / "Season 01").mkdir(parents=True)
    response = await client.get("/api/directories/tree", params={"path": str(root)})
    assert response.status_code == 200
    names = [e["name"] for e in response.json()["entries"]]
    assert names == ["Season 01"]
