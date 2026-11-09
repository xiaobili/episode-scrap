from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

import httpx


class JellyfinError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class JellyfinAuthError(JellyfinError):
    pass


@dataclass
class JellyfinLibrary:
    id: str
    name: str
    collection_type: str | None = None


class JellyfinClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: int = 10,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        parsed = urlparse(base_url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise JellyfinError("Jellyfin 服务地址必须是合法的 http/https URL")
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._client = httpx.AsyncClient(timeout=timeout, transport=transport)

    async def close(self) -> None:
        await self._client.aclose()

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f'MediaBrowser Token="{self.api_key}"'}

    async def _request(
        self, method: str, path: str, params: dict[str, str] | None = None
    ) -> httpx.Response:
        try:
            response = await self._client.request(
                method, f"{self.base_url}{path}", headers=self._headers(), params=params
            )
        except httpx.HTTPError as exc:
            raise JellyfinError(f"无法连接 Jellyfin：{exc}", 502) from exc
        if response.status_code in (401, 403):
            raise JellyfinAuthError("Jellyfin 认证失败，请检查 API Key", 401)
        if response.status_code >= 400:
            raise JellyfinError(f"Jellyfin 请求失败（{response.status_code}）", 502)
        return response

    async def test_connection(self) -> dict[str, str]:
        response = await self._request("GET", "/System/Info")
        data = response.json()
        return {
            "server_name": data.get("ServerName", ""),
            "version": data.get("Version", ""),
        }

    async def list_libraries(self) -> list[JellyfinLibrary]:
        response = await self._request("GET", "/Library/MediaFolders")
        items = response.json().get("Items") or []
        return [
            JellyfinLibrary(
                id=item.get("Id", ""),
                name=item.get("Name", ""),
                collection_type=item.get("CollectionType"),
            )
            for item in items
            if item.get("Id")
        ]

    async def refresh_library(self, item_id: str) -> None:
        await self._request(
            "POST",
            f"/Items/{item_id}/Refresh",
            params={
                "metadataRefreshMode": "Default",
                "imageRefreshMode": "Default",
                "replaceAllMetadata": "false",
                "replaceAllImages": "false",
                "recursive": "true",
            },
        )
