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


async def test_strm_settings_roundtrip(client):
    response = await client.put(
        "/api/settings",
        json={
            "strm_url_template": "{base_url}/p/{path}",
            "strm_output_mode": "library",
            "strm_target_dir": "/tmp/strm-library",
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["strm_url_template"] == "{base_url}/p/{path}"
    assert data["strm_output_mode"] == "library"
    assert data["strm_target_dir"] == "/tmp/strm-library"


async def test_invalid_strm_template_rejected(client):
    response = await client.put(
        "/api/settings", json={"strm_url_template": "{base_url}/d/"}
    )
    assert response.status_code == 400


async def test_relative_strm_target_rejected(client):
    response = await client.put(
        "/api/settings", json={"strm_target_dir": "relative/dir"}
    )
    assert response.status_code == 400


async def test_strm_rules_roundtrip(client):
    response = await client.put(
        "/api/settings",
        json={
            "strm_rules": [
                {
                    "source": "/cloud/美剧",
                    "target_type": "local",
                    "target_dir": "/media/strm/美剧",
                }
            ]
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["strm_rules"] == [
        {
            "source": "/cloud/美剧",
            "target_type": "local",
            "target_id": None,
            "target_dir": "/media/strm/美剧",
        }
    ]


async def test_strm_rule_requires_absolute_source(client):
    response = await client.put(
        "/api/settings",
        json={"strm_rules": [{"source": "cloud/美剧", "target_dir": "/strm"}]},
    )
    assert response.status_code == 400


async def test_strm_rule_requires_valid_instance(client):
    response = await client.put(
        "/api/settings",
        json={
            "strm_rules": [
                {
                    "source": "/cloud/美剧",
                    "target_type": "openlist",
                    "target_id": 999999,
                    "target_dir": "/strm/美剧",
                }
            ]
        },
    )
    assert response.status_code == 400


async def test_jellyfin_settings_roundtrip(client):
    clear_setting("jellyfin_url")
    clear_setting("jellyfin_api_key")

    defaults = await client.get("/api/settings")
    assert defaults.json()["jellyfin_url"] == ""
    assert defaults.json()["has_jellyfin_key"] is False

    response = await client.put(
        "/api/settings",
        json={"jellyfin_url": "http://jellyfin.local:8096/", "jellyfin_api_key": "jf-secret"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["jellyfin_url"] == "http://jellyfin.local:8096"
    assert data["has_jellyfin_key"] is True
    assert "jf-secret" not in response.text

    with Session(engine) as session:
        row = session.get(Setting, "jellyfin_api_key")
        assert row is not None
        assert row.value != "jf-secret"
        assert decrypt(row.value) == "jf-secret"


async def test_invalid_jellyfin_url_rejected(client):
    response = await client.put("/api/settings", json={"jellyfin_url": "not-a-url"})
    assert response.status_code == 400


async def test_empty_jellyfin_key_does_not_overwrite(client):
    await client.put("/api/settings", json={"jellyfin_api_key": "keep-me"})
    await client.put("/api/settings", json={"jellyfin_api_key": ""})
    with Session(engine) as session:
        row = session.get(Setting, "jellyfin_api_key")
        assert row is not None
        assert decrypt(row.value) == "keep-me"
