from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.clients.jellyfin import JellyfinAuthError, JellyfinClient, JellyfinError
from app.db import get_session
from app.schemas import (
    JellyfinLibraryOut,
    JellyfinRefreshOut,
    JellyfinRefreshRequest,
    JellyfinRefreshResult,
    TestConnectionOut,
)
from app.services.settings import get_jellyfin_key, get_jellyfin_url

router = APIRouter(tags=["jellyfin"])


async def get_jellyfin_client(
    session: Session = Depends(get_session),
) -> AsyncIterator[JellyfinClient]:
    url = get_jellyfin_url(session)
    key = get_jellyfin_key(session)
    if not url or not key:
        raise HTTPException(
            status_code=400, detail="请先在设置中配置 Jellyfin 地址与 API Key"
        )
    client = JellyfinClient(base_url=url, api_key=key)
    try:
        yield client
    finally:
        await client.close()


def _raise_for(exc: JellyfinError) -> None:
    if isinstance(exc, JellyfinAuthError):
        raise HTTPException(status_code=401, detail=exc.message) from exc
    raise HTTPException(status_code=502, detail=exc.message) from exc


@router.get("/api/jellyfin/libraries", response_model=list[JellyfinLibraryOut])
async def list_libraries(
    client: JellyfinClient = Depends(get_jellyfin_client),
) -> list[JellyfinLibraryOut]:
    try:
        libraries = await client.list_libraries()
    except JellyfinError as exc:
        _raise_for(exc)
    return [
        JellyfinLibraryOut(
            id=lib.id, name=lib.name, collection_type=lib.collection_type
        )
        for lib in libraries
    ]


@router.post("/api/jellyfin/refresh", response_model=JellyfinRefreshOut)
async def refresh_libraries(
    payload: JellyfinRefreshRequest,
    client: JellyfinClient = Depends(get_jellyfin_client),
) -> JellyfinRefreshOut:
    if not payload.library_ids:
        raise HTTPException(status_code=400, detail="请选择要刷新的媒体库")
    results: list[JellyfinRefreshResult] = []
    for library_id in payload.library_ids:
        try:
            await client.refresh_library(library_id)
            results.append(JellyfinRefreshResult(library_id=library_id, ok=True))
        except JellyfinError as exc:
            results.append(
                JellyfinRefreshResult(library_id=library_id, ok=False, error=exc.message)
            )
    return JellyfinRefreshOut(results=results)


@router.post("/api/jellyfin/test", response_model=TestConnectionOut)
async def test_connection(
    client: JellyfinClient = Depends(get_jellyfin_client),
) -> TestConnectionOut:
    try:
        info = await client.test_connection()
    except JellyfinError as exc:
        _raise_for(exc)
    return TestConnectionOut(
        ok=True, message=f"连接成功：{info['server_name']}（{info['version']}）"
    )
