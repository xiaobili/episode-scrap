import httpx
import pytest

from app.clients.jellyfin import JellyfinAuthError, JellyfinClient, JellyfinError


def make_client(handler):
    return JellyfinClient(
        base_url="https://jellyfin.example.com",
        api_key="secret-token",
        timeout=5,
        transport=httpx.MockTransport(handler),
    )


async def test_test_connection_returns_server_info():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/System/Info"
        assert request.headers["authorization"] == 'MediaBrowser Token="secret-token"'
        return httpx.Response(
            200, json={"ServerName": "demo", "Version": "10.9.11"}
        )

    client = make_client(handler)
    info = await client.test_connection()
    assert info["server_name"] == "demo"
    assert info["version"] == "10.9.11"
    await client.close()


async def test_list_libraries():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/Library/MediaFolders"
        assert request.headers["authorization"] == 'MediaBrowser Token="secret-token"'
        return httpx.Response(
            200,
            json={
                "Items": [
                    {"Name": "剧集", "Id": "lib1", "CollectionType": "tvshows"},
                    {"Name": "电影", "Id": "lib2", "CollectionType": "movies"},
                ]
            },
        )

    client = make_client(handler)
    libraries = await client.list_libraries()
    assert [(lib.id, lib.name, lib.collection_type) for lib in libraries] == [
        ("lib1", "剧集", "tvshows"),
        ("lib2", "电影", "movies"),
    ]
    await client.close()


async def test_refresh_library_posts_to_item():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path, dict(request.url.params)))
        assert request.headers["authorization"] == 'MediaBrowser Token="secret-token"'
        return httpx.Response(204)

    client = make_client(handler)
    await client.refresh_library("lib1")
    assert calls == [
        (
            "POST",
            "/Items/lib1/Refresh",
            {
                "metadataRefreshMode": "Default",
                "imageRefreshMode": "Default",
                "replaceAllMetadata": "false",
                "replaceAllImages": "false",
                "recursive": "true",
            },
        )
    ]
    await client.close()


async def test_auth_error_raises():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={})

    client = make_client(handler)
    with pytest.raises(JellyfinAuthError):
        await client.list_libraries()
    await client.close()


async def test_server_error_raises():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    client = make_client(handler)
    with pytest.raises(JellyfinError):
        await client.refresh_library("lib1")
    await client.close()


def test_invalid_base_url_rejected():
    with pytest.raises(JellyfinError):
        JellyfinClient(base_url="not-a-url", api_key="k")
