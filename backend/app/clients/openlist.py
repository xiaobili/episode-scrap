from __future__ import annotations

import asyncio
from urllib.parse import quote, urlparse

import httpx

from app.datasources.base import FileEntry


class OpenListError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class OpenListAuthError(OpenListError):
    pass


def _entry(path: str, item: dict) -> FileEntry:
    return FileEntry(
        name=item.get("name", ""),
        path=f"{path.rstrip('/')}/{item.get('name', '')}",
        size=int(item.get("size") or 0),
        is_dir=bool(item.get("is_dir")),
        modified_at=item.get("modified"),
    )


class OpenListClient:
    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        timeout: int = 30,
        retry: int = 3,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        parsed = urlparse(base_url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise OpenListError("OpenList 服务地址必须是合法的 http/https URL")
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.retry = max(retry, 0)
        self._token: str | None = None
        self._client = httpx.AsyncClient(timeout=timeout, transport=transport)

    async def close(self) -> None:
        await self._client.aclose()

    async def login(self) -> str:
        response = await self._client.post(
            f"{self.base_url}/api/auth/login",
            json={"username": self.username, "password": self.password},
        )
        if response.status_code >= 400:
            raise OpenListAuthError("OpenList 登录失败，请检查用户名与密码", 401)
        payload = response.json()
        token = (payload.get("data") or {}).get("token")
        if not token:
            raise OpenListAuthError(payload.get("message") or "OpenList 登录失败", 401)
        self._token = token
        return token

    async def _ensure_token(self) -> None:
        if not self._token:
            await self.login()

    def _auth_headers(self) -> dict[str, str]:
        return {"Authorization": self._token or ""}

    async def list(
        self, path: str, recursive: bool = False, refresh: bool = False
    ) -> list[FileEntry]:
        data = await self._request(
            "POST",
            "/api/fs/list",
            json={"path": path, "page": 1, "per_page": 0, "refresh": refresh},
        )
        entries = [_entry(path, item) for item in data.get("content") or []]
        if recursive:
            for entry in list(entries):
                if entry.is_dir:
                    entries.extend(
                        await self.list(entry.path, recursive=True, refresh=refresh)
                    )
        return entries

    async def get(self, path: str) -> FileEntry | None:
        data = await self._request("POST", "/api/fs/get", json={"path": path})
        if not data:
            return None
        return _entry(path.rsplit("/", 1)[0] or "/", data)

    async def rename(self, path: str, new_name: str) -> None:
        await self._request("POST", "/api/fs/rename", json={"path": path, "name": new_name})

    async def batch_rename(self, items: list[tuple[str, str]]) -> None:
        await self._request(
            "POST",
            "/api/fs/batch_rename",
            json={"rename_objects": [{"path": p, "new_name": n} for p, n in items]},
        )

    async def upload(self, dir_path: str, filename: str, content: bytes) -> None:
        full_path = f"{dir_path.rstrip('/')}/{filename}"
        await self._request(
            "PUT",
            "/api/fs/put",
            headers_patch=True,
            content=content,
            extra_headers={
                # HTTP 头只能承载 ASCII，路径需按 AList/OpenList 约定做 URL 编码
                "File-Path": quote(full_path, safe="/"),
                "Content-Type": "application/octet-stream",
            },
        )

    async def mkdir(self, path: str) -> None:
        await self._request("POST", "/api/fs/mkdir", json={"path": path})

    async def _request(self, method: str, path: str, **kwargs) -> dict:  # type: ignore[no-redef]
        extra_headers = kwargs.pop("extra_headers", None)
        kwargs.pop("headers_patch", None)
        refreshed = False
        last_error: Exception | None = None
        for attempt in range(self.retry + 2):
            await self._ensure_token()
            headers = self._auth_headers()
            if extra_headers:
                headers.update(extra_headers)
            try:
                response = await self._client.request(
                    method, f"{self.base_url}{path}", headers=headers, **kwargs
                )
            except httpx.TimeoutException as exc:
                last_error = exc
                if attempt < self.retry:
                    await asyncio.sleep(min(0.5 * (2**attempt), 30))
                    continue
                raise OpenListError("OpenList 请求超时", 504) from exc

            if response.status_code == 401:
                if not refreshed:
                    refreshed = True
                    self._token = None
                    await self.login()
                    continue
                raise OpenListAuthError("OpenList Token 无效或已过期", 401)

            if response.status_code == 429 or response.status_code >= 500:
                last_error = OpenListError(
                    f"OpenList 服务暂不可用（{response.status_code}）", response.status_code
                )
                if attempt < self.retry:
                    await asyncio.sleep(min(0.5 * (2**attempt), 30))
                    continue
                raise last_error

            if response.status_code >= 400:
                raise OpenListError(
                    f"OpenList 请求失败：{response.text[:200]}", response.status_code
                )

            try:
                payload = response.json()
            except ValueError as exc:
                raise OpenListError("OpenList 返回了非 JSON 响应") from exc
            code = payload.get("code", 200)
            if code == 401:
                if not refreshed:
                    refreshed = True
                    self._token = None
                    await self.login()
                    continue
                raise OpenListAuthError("OpenList Token 无效或已过期", 401)
            if code not in (200, 0):
                raise OpenListError(payload.get("message") or f"OpenList 错误码 {code}")
            return payload.get("data") or {}
        raise OpenListError(str(last_error or "OpenList 请求失败"))
