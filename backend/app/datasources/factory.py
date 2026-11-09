import os

from sqlmodel import Session

from app.datasources.base import BaseDataSource
from app.datasources.local import LocalDataSource
from app.models import OpenListInstance
from app.services.crypto import decrypt
from app.services.settings import get_openlist_options


class DataSourceError(ValueError):
    pass


_openlist_cache: dict[int, BaseDataSource] = {}


def clear_openlist_cache(instance_id: int) -> None:
    _openlist_cache.pop(instance_id, None)


def get_datasource(
    session: Session, source_type: str, openlist_id: int | None = None
) -> BaseDataSource:
    if source_type == "local":
        return LocalDataSource()
    if source_type == "openlist":
        if openlist_id is None:
            raise DataSourceError("OpenList 数据源需要指定实例")
        if openlist_id in _openlist_cache:
            return _openlist_cache[openlist_id]
        instance = session.get(OpenListInstance, openlist_id)
        if not instance:
            raise DataSourceError("OpenList 实例不存在")
        from app.clients.openlist import OpenListClient
        from app.datasources.openlist import OpenListDataSource

        options = get_openlist_options(session)
        client = OpenListClient(
            base_url=instance.base_url,
            username=instance.username,
            password=decrypt(instance.password_encrypted),
            timeout=instance.timeout or options["timeout"],
            retry=options["retry"],
        )
        datasource = OpenListDataSource(client)
        _openlist_cache[openlist_id] = datasource
        return datasource
    raise DataSourceError(f"未知数据源：{source_type}")
