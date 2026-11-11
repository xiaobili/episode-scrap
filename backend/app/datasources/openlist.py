from __future__ import annotations

from app.clients.openlist import OpenListClient, OpenListError
from app.datasources.base import BaseDataSource, FileEntry


class OpenListDataSource(BaseDataSource):
    name = "openlist"

    def __init__(self, client: OpenListClient):
        self.client = client

    async def list_dir(
        self, path: str, recursive: bool = False, refresh: bool = False
    ) -> list[FileEntry]:
        return await self.client.list(path, recursive=recursive, refresh=refresh)

    async def get_file(self, path: str) -> FileEntry | None:
        return await self.client.get(path)

    async def rename(self, path: str, new_name: str) -> str:
        await self.client.rename(path, new_name)
        return self.join(path.rsplit("/", 1)[0] or "/", new_name)

    async def batch_rename(self, items: list[tuple[str, str]]) -> None:
        await self.client.batch_rename(items)

    async def upload(self, dir_path: str, content: bytes, filename: str) -> None:
        await self.client.upload(dir_path, filename, content)

    async def mkdir(self, path: str) -> None:
        await self.client.mkdir(path)

    async def exists(self, dir_path: str, name: str) -> bool:
        try:
            entries = await self.client.list(dir_path)
        except OpenListError:
            return False
        return any(entry.name == name for entry in entries)
