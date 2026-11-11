import json
from urllib.parse import unquote

import httpx
import pytest

from app.clients.openlist import OpenListAuthError, OpenListClient


def make_client(handler, retry=0):
    return OpenListClient(
        base_url="https://openlist.example.com",
        username="admin",
        password="secret",
        timeout=5,
        retry=retry,
        transport=httpx.MockTransport(handler),
    )


async def test_login_and_list():
    calls = {"login": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/auth/login":
            calls["login"] += 1
            return httpx.Response(200, json={"code": 200, "data": {"token": "t1"}})
        assert request.headers["authorization"] == "t1"
        return httpx.Response(
            200,
            json={
                "code": 200,
                "data": {
                    "content": [
                        {"name": "Show", "is_dir": True, "size": 0},
                        {"name": "a.mkv", "is_dir": False, "size": 10, "modified": "2026-01-01"},
                    ]
                },
            },
        )

    client = make_client(handler)
    entries = await client.list("/root")
    assert calls["login"] == 1
    assert [e.name for e in entries] == ["Show", "a.mkv"]
    assert entries[1].path == "/root/a.mkv"
    await client.close()


async def test_token_refreshed_once_on_401():
    calls = {"login": 0, "list": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/auth/login":
            calls["login"] += 1
            return httpx.Response(200, json={"code": 200, "data": {"token": f"t{calls['login']}"}})
        calls["list"] += 1
        if calls["list"] == 1:
            return httpx.Response(401, json={"code": 401})
        return httpx.Response(200, json={"code": 200, "data": {"content": []}})

    client = make_client(handler)
    assert await client.list("/root") == []
    assert calls["login"] == 2
    await client.close()


async def test_auth_failure_raises():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"code": 401})

    client = make_client(handler)
    with pytest.raises(OpenListAuthError):
        await client.list("/root")
    await client.close()


async def test_list_can_force_refresh():
    captured = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/auth/login":
            return httpx.Response(200, json={"code": 200, "data": {"token": "t"}})
        captured.append(json.loads(request.content))
        return httpx.Response(200, json={"code": 200, "data": {"content": []}})

    client = make_client(handler)
    await client.list("/root")
    await client.list("/root", refresh=True)
    assert captured[0]["refresh"] is False
    assert captured[1]["refresh"] is True
    await client.close()


async def test_recursive_list():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/auth/login":
            return httpx.Response(200, json={"code": 200, "data": {"token": "t"}})
        payload = json.loads(request.content or b"{}")
        if payload.get("path") == "/root":
            content = [{"name": "S1", "is_dir": True, "size": 0}]
        else:
            content = [{"name": "ep.mkv", "is_dir": False, "size": 3}]
        return httpx.Response(200, json={"code": 200, "data": {"content": content}})

    client = make_client(handler)
    entries = await client.list("/root", recursive=True)
    assert [e.path for e in entries] == ["/root/S1", "/root/S1/ep.mkv"]
    await client.close()


async def test_rename_and_batch_payload():
    captured = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/auth/login":
            return httpx.Response(200, json={"code": 200, "data": {"token": "t"}})
        captured.append((request.url.path, json.loads(request.content)))
        return httpx.Response(200, json={"code": 200, "data": {}})

    client = make_client(handler)
    await client.rename("/root/a.mkv", "b.mkv")
    await client.batch_rename([("/root/a.mkv", "b.mkv")])
    assert captured[0] == ("/api/fs/rename", {"path": "/root/a.mkv", "name": "b.mkv"})
    assert captured[1][1] == {"rename_objects": [{"path": "/root/a.mkv", "new_name": "b.mkv"}]}
    await client.close()


async def test_upload_sets_file_path_header():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/auth/login":
            return httpx.Response(200, json={"code": 200, "data": {"token": "t"}})
        captured["file_path"] = request.headers.get("file-path")
        captured["content_type"] = request.headers.get("content-type")
        captured["body"] = request.content
        return httpx.Response(200, json={"code": 200, "data": {}})

    client = make_client(handler)
    await client.upload("/root/Show", "Show.nfo", b"<xml/>")
    assert captured["file_path"] == "/root/Show/Show.nfo"
    assert captured["content_type"] == "application/octet-stream"
    assert captured["body"] == b"<xml/>"
    await client.close()


async def test_upload_encodes_non_ascii_path_header():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/auth/login":
            return httpx.Response(200, json={"code": 200, "data": {"token": "t"}})
        captured["file_path"] = request.headers.get("file-path")
        return httpx.Response(200, json={"code": 200, "data": {}})

    client = make_client(handler)
    await client.upload("/媒体/剧集", "夜班经理 - S01E01.nfo", b"<xml/>")
    header = captured["file_path"]
    assert header.isascii()
    assert unquote(header) == "/媒体/剧集/夜班经理 - S01E01.nfo"
    await client.close()


async def test_instance_crud_never_returns_password(client):
    created = await client.post(
        "/api/datasources/openlist",
        json={
            "name": "家庭云盘",
            "base_url": "https://fox.oplist.org",
            "username": "admin",
            "password": "secret",
            "timeout": 30,
            "concurrency": 3,
        },
    )
    assert created.status_code == 200, created.text
    data = created.json()
    assert "password" not in data
    assert data["has_password"] is True

    listed = await client.get("/api/datasources")
    assert any(item["type"] == "openlist" for item in listed.json())

    updated = await client.put(
        f"/api/datasources/openlist/{data['id']}", json={"name": "备用实例"}
    )
    assert updated.json()["name"] == "备用实例"

    deleted = await client.delete(f"/api/datasources/openlist/{data['id']}")
    assert deleted.json() == {"ok": True}


async def test_instance_rejects_invalid_url(client):
    response = await client.post(
        "/api/datasources/openlist",
        json={
            "name": "bad",
            "base_url": "file:///etc/passwd",
            "username": "admin",
            "password": "secret",
        },
    )
    assert response.status_code == 400
