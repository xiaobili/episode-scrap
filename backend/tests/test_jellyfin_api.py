import pytest
from sqlmodel import Session

from app.clients.jellyfin import JellyfinError
from app.db import engine
from app.main import app
from app.models import Setting


class FakeJellyfinClient:
    def __init__(self, libraries=None, fail_on=None, info=None):
        self.libraries = libraries or []
        self.fail_on = set(fail_on or [])
        self.info = info or {"server_name": "demo", "version": "10.9.11"}
        self.refreshed = []

    async def list_libraries(self):
        return self.libraries

    async def refresh_library(self, item_id: str):
        if item_id in self.fail_on:
            raise JellyfinError("刷新失败")
        self.refreshed.append(item_id)

    async def test_connection(self):
        return self.info


def override_client(fake):
    from app.api.jellyfin import get_jellyfin_client

    async def _override():
        yield fake

    app.dependency_overrides[get_jellyfin_client] = _override


def clear_override():
    from app.api.jellyfin import get_jellyfin_client

    app.dependency_overrides.pop(get_jellyfin_client, None)


def clear_setting(key: str) -> None:
    with Session(engine) as session:
        row = session.get(Setting, key)
        if row:
            session.delete(row)
            session.commit()


@pytest.fixture(autouse=True)
def _cleanup():
    yield
    clear_override()


async def test_libraries_requires_config(client):
    clear_setting("jellyfin_url")
    clear_setting("jellyfin_api_key")
    response = await client.get("/api/jellyfin/libraries")
    assert response.status_code == 400


async def test_list_libraries(client):
    from app.clients.jellyfin import JellyfinLibrary

    fake = FakeJellyfinClient(
        libraries=[
            JellyfinLibrary(id="lib1", name="剧集", collection_type="tvshows"),
            JellyfinLibrary(id="lib2", name="电影", collection_type="movies"),
        ]
    )
    override_client(fake)
    response = await client.get("/api/jellyfin/libraries")
    assert response.status_code == 200
    assert response.json() == [
        {"id": "lib1", "name": "剧集", "collection_type": "tvshows"},
        {"id": "lib2", "name": "电影", "collection_type": "movies"},
    ]


async def test_refresh_libraries_reports_each_result(client):
    fake = FakeJellyfinClient(fail_on={"lib2"})
    override_client(fake)
    response = await client.post(
        "/api/jellyfin/refresh", json={"library_ids": ["lib1", "lib2"]}
    )
    assert response.status_code == 200
    results = response.json()["results"]
    assert results[0] == {"library_id": "lib1", "ok": True, "error": None}
    assert results[1]["library_id"] == "lib2"
    assert results[1]["ok"] is False
    assert results[1]["error"]
    assert fake.refreshed == ["lib1"]


async def test_refresh_requires_ids(client):
    override_client(FakeJellyfinClient())
    response = await client.post("/api/jellyfin/refresh", json={"library_ids": []})
    assert response.status_code == 400


async def test_test_connection(client):
    override_client(FakeJellyfinClient(info={"server_name": "demo", "version": "10.9.11"}))
    response = await client.post("/api/jellyfin/test")
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert "demo" in data["message"]
