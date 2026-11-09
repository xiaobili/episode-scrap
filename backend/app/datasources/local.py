import asyncio
import os
from datetime import datetime

from app.datasources.base import BaseDataSource, FileEntry


def _modified(path: str) -> str:
    return datetime.fromtimestamp(os.path.getmtime(path)).isoformat(timespec="seconds")


class LocalDataSource(BaseDataSource):
    name = "local"

    async def list_dir(self, path: str, recursive: bool = False) -> list[FileEntry]:
        return await asyncio.to_thread(self._list_dir, path, recursive)

    def _list_dir(self, path: str, recursive: bool) -> list[FileEntry]:
        entries: list[FileEntry] = []
        if recursive:
            for root, _dirs, files in os.walk(path):
                for name in files:
                    full = os.path.join(root, name)
                    entries.append(
                        FileEntry(
                            name=name,
                            path=full,
                            size=os.path.getsize(full),
                            is_dir=False,
                            modified_at=_modified(full),
                        )
                    )
        else:
            with os.scandir(path) as iterator:
                for item in iterator:
                    if item.is_dir():
                        continue
                    entries.append(
                        FileEntry(
                            name=item.name,
                            path=item.path,
                            size=item.stat().st_size,
                            is_dir=False,
                            modified_at=_modified(item.path),
                        )
                    )
        return entries

    async def get_file(self, path: str) -> FileEntry | None:
        if not os.path.isfile(path):
            return None
        return FileEntry(
            name=os.path.basename(path),
            path=path,
            size=os.path.getsize(path),
            is_dir=False,
            modified_at=_modified(path),
        )

    async def rename(self, path: str, new_name: str) -> str:
        new_path = os.path.join(os.path.dirname(path), new_name)
        if os.path.exists(new_path) and os.path.realpath(new_path) != os.path.realpath(path):
            raise FileExistsError(f"目标文件已存在：{new_name}")
        os.rename(path, new_path)
        return new_path

    async def batch_rename(self, items: list[tuple[str, str]]) -> None:
        for path, new_name in items:
            await self.rename(path, new_name)

    async def upload(self, dir_path: str, content: bytes, filename: str) -> None:
        with open(os.path.join(dir_path, filename), "wb") as file:
            file.write(content)

    async def mkdir(self, path: str) -> None:
        os.makedirs(path, exist_ok=True)

    async def exists(self, dir_path: str, name: str) -> bool:
        return os.path.exists(os.path.join(dir_path, name))
