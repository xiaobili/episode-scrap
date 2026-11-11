import os
import time

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete
from sqlmodel import Session, select

from app.core.parser import is_video_filename
from app.datasources.base import FileEntry
from app.datasources.factory import DataSourceError, get_datasource
from app.db import get_session
from app.models import MediaFile, ScrapeMatch
from app.schemas import (
    MediaFileOut,
    ScanRequest,
    ScanResponse,
    TreeEntry,
    TreeResponse,
    media_file_out,
)
from app.services.paths import ensure_allowed, normalize
from app.services.settings import get_allowed_paths

router = APIRouter(tags=["scan"])


def _openlist_condition(openlist_id: int | None):
    if openlist_id is None:
        return MediaFile.openlist_id.is_(None)
    return MediaFile.openlist_id == openlist_id


@router.post("/api/scan", response_model=ScanResponse)
async def scan(payload: ScanRequest, session: Session = Depends(get_session)) -> ScanResponse:
    started = time.perf_counter()
    try:
        if payload.source_type == "local":
            roots = get_allowed_paths(session)
            root = ensure_allowed(payload.source_ref, roots)
            if not os.path.isdir(root):
                raise HTTPException(status_code=400, detail=f"目录不存在：{payload.source_ref}")
            datasource = get_datasource(session, "local")
        else:
            from app.models import OpenListInstance

            instance = session.get(OpenListInstance, payload.openlist_id)
            if not instance:
                raise HTTPException(status_code=400, detail="OpenList 实例不存在")
            root = payload.source_ref or instance.mount_path or "/"
            if not root.startswith("/"):
                raise HTTPException(status_code=400, detail="OpenList 路径必须以 / 开头")
            datasource = get_datasource(session, "openlist", payload.openlist_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except DataSourceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        entries = await datasource.list_dir(root, recursive=payload.recursive)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"目录不存在：{root}") from exc
    except Exception as exc:  # OpenList 网络/鉴权错误
        raise HTTPException(status_code=502, detail=f"读取目录失败：{exc}") from exc

    entries = sorted([e for e in entries if not e.is_dir], key=lambda e: e.path)

    stale = session.exec(
        select(MediaFile).where(
            MediaFile.source_type == payload.source_type,
            MediaFile.scan_root == root,
            _openlist_condition(payload.openlist_id),
        )
    ).all()
    stale_ids = [f.id for f in stale if f.id is not None]
    if stale_ids:
        session.exec(delete(ScrapeMatch).where(ScrapeMatch.file_id.in_(stale_ids)))
        session.exec(delete(MediaFile).where(MediaFile.id.in_(stale_ids)))
        session.commit()

    files: list[MediaFile] = []
    for entry in entries:
        media = MediaFile(
            source_type=payload.source_type,
            source_ref=entry.path,
            scan_root=root,
            openlist_id=payload.openlist_id,
            original_name=entry.name,
            size=entry.size,
            modified_at=entry.modified_at,
            is_video=is_video_filename(entry.name),
        )
        session.add(media)
        files.append(media)
    session.commit()
    for media in files:
        session.refresh(media)

    video_count = sum(1 for f in files if f.is_video)
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    return ScanResponse(
        files=[media_file_out(f) for f in files],
        total=len(files),
        video_count=video_count,
        other_count=len(files) - video_count,
        elapsed_ms=elapsed_ms,
    )


@router.get("/api/files", response_model=list[MediaFileOut])
def list_files(
    source_type: str | None = None,
    openlist_id: int | None = None,
    limit: int = Query(default=1000, le=5000),
    session: Session = Depends(get_session),
) -> list[MediaFileOut]:
    stmt = select(MediaFile)
    if source_type:
        stmt = stmt.where(MediaFile.source_type == source_type)
    if openlist_id is not None:
        stmt = stmt.where(MediaFile.openlist_id == openlist_id)
    stmt = stmt.order_by(MediaFile.scanned_at.desc(), MediaFile.id).limit(limit)
    return [media_file_out(f) for f in session.exec(stmt).all()]


@router.get("/api/directories/tree", response_model=TreeResponse)
def directory_tree(
    path: str = "", session: Session = Depends(get_session)
) -> TreeResponse:
    roots = get_allowed_paths(session)
    if not path:
        entries = [
            TreeEntry(name=os.path.basename(normalize(r)) or normalize(r), path=normalize(r))
            for r in roots
        ]
        return TreeResponse(path="", parent=None, entries=entries)

    try:
        target = ensure_allowed(path, roots)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    if not os.path.isdir(target):
        raise HTTPException(status_code=404, detail=f"目录不存在：{path}")

    entries: list[TreeEntry] = []
    try:
        with os.scandir(target) as iterator:
            for item in iterator:
                if item.is_dir():
                    entries.append(
                        TreeEntry(name=item.name, path=item.path, is_dir=True)
                    )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    entries.sort(key=lambda e: e.name)

    root_set = {normalize(r) for r in roots}
    parent = None if target in root_set else os.path.dirname(target)
    return TreeResponse(path=target, parent=parent, entries=entries)
