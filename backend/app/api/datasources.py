import os
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.clients.openlist import OpenListAuthError, OpenListClient, OpenListError
from app.datasources.factory import clear_openlist_cache, get_datasource
from app.db import get_session
from app.models import OpenListInstance
from app.schemas import (
    DataSourceOut,
    OpenListCreate,
    OpenListOut,
    OpenListUpdate,
    TestConnectionOut,
    TreeEntry,
    TreeResponse,
)
from app.services.crypto import encrypt
from app.services.settings import get_openlist_options

router = APIRouter(tags=["datasources"])


def _validate_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise HTTPException(status_code=400, detail="服务地址必须是合法的 http/https URL")
    return url.rstrip("/")


def _to_out(instance: OpenListInstance) -> OpenListOut:
    return OpenListOut(
        id=instance.id or 0,
        name=instance.name,
        base_url=instance.base_url,
        username=instance.username,
        timeout=instance.timeout,
        concurrency=instance.concurrency,
        has_password=bool(instance.password_encrypted),
        created_at=instance.created_at,
    )


@router.get("/api/datasources", response_model=list[DataSourceOut])
def list_datasources(session: Session = Depends(get_session)) -> list[DataSourceOut]:
    items = [
        DataSourceOut(type="local", id=None, name="本地文件系统", base_url=None, username=None)
    ]
    for instance in session.exec(select(OpenListInstance)).all():
        items.append(
            DataSourceOut(
                type="openlist",
                id=instance.id,
                name=instance.name,
                base_url=instance.base_url,
                username=instance.username,
            )
        )
    return items


@router.get("/api/datasources/openlist", response_model=list[OpenListOut])
def list_openlist_instances(
    session: Session = Depends(get_session),
) -> list[OpenListOut]:
    return [_to_out(i) for i in session.exec(select(OpenListInstance)).all()]


@router.post("/api/datasources/openlist", response_model=OpenListOut)
def create_openlist_instance(
    payload: OpenListCreate, session: Session = Depends(get_session)
) -> OpenListOut:
    instance = OpenListInstance(
        name=payload.name.strip() or "OpenList",
        base_url=_validate_url(payload.base_url),
        username=payload.username,
        password_encrypted=encrypt(payload.password),
        timeout=payload.timeout,
        concurrency=payload.concurrency,
    )
    session.add(instance)
    session.commit()
    session.refresh(instance)
    return _to_out(instance)


@router.put("/api/datasources/openlist/{instance_id}", response_model=OpenListOut)
def update_openlist_instance(
    instance_id: int, payload: OpenListUpdate, session: Session = Depends(get_session)
) -> OpenListOut:
    instance = session.get(OpenListInstance, instance_id)
    if not instance:
        raise HTTPException(status_code=404, detail="OpenList 实例不存在")

    if payload.name is not None:
        instance.name = payload.name
    if payload.base_url is not None:
        instance.base_url = _validate_url(payload.base_url)
    if payload.username is not None:
        instance.username = payload.username
    if payload.password:
        instance.password_encrypted = encrypt(payload.password)
    if payload.timeout is not None:
        instance.timeout = payload.timeout
    if payload.concurrency is not None:
        instance.concurrency = payload.concurrency

    session.add(instance)
    session.commit()
    session.refresh(instance)
    clear_openlist_cache(instance_id)
    return _to_out(instance)


@router.delete("/api/datasources/openlist/{instance_id}")
def delete_openlist_instance(
    instance_id: int, session: Session = Depends(get_session)
) -> dict[str, bool]:
    instance = session.get(OpenListInstance, instance_id)
    if not instance:
        raise HTTPException(status_code=404, detail="OpenList 实例不存在")
    session.delete(instance)
    session.commit()
    clear_openlist_cache(instance_id)
    return {"ok": True}


@router.post("/api/datasources/openlist/{instance_id}/test", response_model=TestConnectionOut)
async def test_openlist_instance(
    instance_id: int, session: Session = Depends(get_session)
) -> TestConnectionOut:
    instance = session.get(OpenListInstance, instance_id)
    if not instance:
        raise HTTPException(status_code=404, detail="OpenList 实例不存在")
    from app.services.crypto import decrypt

    options = get_openlist_options(session)
    try:
        client = OpenListClient(
            base_url=instance.base_url,
            username=instance.username,
            password=decrypt(instance.password_encrypted),
            timeout=instance.timeout or options["timeout"],
            retry=0,
        )
        try:
            await client.login()
        finally:
            await client.close()
        return TestConnectionOut(ok=True, message="连接成功")
    except OpenListAuthError as exc:
        raise HTTPException(status_code=401, detail=exc.message) from exc
    except OpenListError as exc:
        raise HTTPException(status_code=502, detail=exc.message) from exc


@router.get(
    "/api/datasources/openlist/{instance_id}/tree", response_model=TreeResponse
)
async def openlist_tree(
    instance_id: int,
    path: str = "/",
    refresh: bool = False,
    session: Session = Depends(get_session),
) -> TreeResponse:
    if not path.startswith("/"):
        raise HTTPException(status_code=400, detail="OpenList 路径必须以 / 开头")
    try:
        datasource = get_datasource(session, "openlist", instance_id)
        entries = await datasource.list_dir(path, refresh=refresh)
    except OpenListAuthError as exc:
        raise HTTPException(status_code=401, detail=exc.message) from exc
    except OpenListError as exc:
        raise HTTPException(status_code=502, detail=exc.message) from exc

    dirs = [
        TreeEntry(name=e.name, path=e.path, is_dir=True)
        for e in entries
        if e.is_dir
    ]
    dirs.sort(key=lambda e: e.name)
    parent = None if path.rstrip("/") in ("", "/") else os.path.dirname(path.rstrip("/"))
    return TreeResponse(path=path, parent=parent, entries=dirs)
