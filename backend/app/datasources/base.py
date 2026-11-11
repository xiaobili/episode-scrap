from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class FileEntry:
    name: str
    path: str
    size: int
    is_dir: bool
    modified_at: str | None = None


class BaseDataSource(ABC):
    name: str

    @abstractmethod
    async def list_dir(
        self, path: str, recursive: bool = False, refresh: bool = False
    ) -> list[FileEntry]:
        """列出目录内容；refresh 表示强制绕过数据源侧缓存（不支持则忽略）。"""
        ...

    @abstractmethod
    async def get_file(self, path: str) -> FileEntry | None: ...

    @abstractmethod
    async def rename(self, path: str, new_name: str) -> str: ...

    @abstractmethod
    async def batch_rename(self, items: list[tuple[str, str]]) -> None: ...

    @abstractmethod
    async def upload(self, dir_path: str, content: bytes, filename: str) -> None: ...

    @abstractmethod
    async def mkdir(self, path: str) -> None: ...

    @abstractmethod
    async def exists(self, dir_path: str, name: str) -> bool: ...

    def join(self, dir_path: str, name: str) -> str:
        return f"{dir_path.rstrip('/')}/{name}"
