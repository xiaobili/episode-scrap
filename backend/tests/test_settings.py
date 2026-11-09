from sqlmodel import Session

from app.db import engine
from app.models import Setting
from app.services.crypto import decrypt


def clear_setting(key: str) -> None:
    with Session(engine) as session:
        row = session.get(Setting, key)
        if row:
            session.delete(row)
            session.commit()


async def test_get_settings_defaults(client):
    clear_setting("tmdb_api_key")
    response = await client.get("/api/settings")
    assert response.status_code == 200
    data = response.json()
    assert "rename_template" in data
    assert data["has_tmdb_key"] is False
    assert isinstance(data["allowed_paths"], list)
    assert "password" not in data


async def test_update_api_key_is_encrypted(client):
    response = await client.put("/api/settings", json={"tmdb_api_key": "my-secret-key"})
    assert response.status_code == 200
    assert response.json()["has_tmdb_key"] is True
    assert "my-secret-key" not in response.text

    with Session(engine) as session:
        row = session.get(Setting, "tmdb_api_key")
        assert row is not None
        assert row.value != "my-secret-key"
        assert decrypt(row.value) == "my-secret-key"


async def test_empty_key_does_not_overwrite(client):
    await client.put("/api/settings", json={"tmdb_api_key": "keep-me"})
    await client.put("/api/settings", json={"tmdb_api_key": ""})
    with Session(engine) as session:
        row = session.get(Setting, "tmdb_api_key")
        assert row is not None
        assert decrypt(row.value) == "keep-me"


async def test_invalid_template_rejected(client):
    response = await client.put("/api/settings", json={"rename_template": "{title} {bad}"})
    assert response.status_code == 400


async def test_allowed_paths_roundtrip(client):
    response = await client.put(
        "/api/settings", json={"allowed_paths": ["/tmp/media", "/tmp/library"]}
    )
    assert response.status_code == 200
    assert response.json()["allowed_paths"] == ["/tmp/media", "/tmp/library"]

    invalid = await client.put("/api/settings", json={"allowed_paths": ["relative/path"]})
    assert invalid.status_code == 400
