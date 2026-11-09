import os
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.core.renamer import TemplateError, parent_of, validate_template
from app.datasources.factory import get_datasource
from app.db import get_session
from app.models import MediaFile, TaskItem, TaskRecord
from app.schemas import (
    RenameExecuteOut,
    RenameExecuteRequest,
    RenamePreviewOut,
    RenamePreviewRequest,
    RollbackOut,
    RollbackRequest,
)
from app.services.rename_service import build_preview
from app.services.settings import get_rename_template
from app.services.task_manager import rollback_task, task_manager

router = APIRouter(tags=["rename"])


async def _select_files(session: Session, file_ids: list[int] | None) -> list[MediaFile]:
    stmt = select(MediaFile).where(MediaFile.is_video.is_(True))
    if file_ids:
        stmt = stmt.where(MediaFile.id.in_(file_ids))
    return list(session.exec(stmt.order_by(MediaFile.id)).all())


@router.post("/api/rename/preview", response_model=RenamePreviewOut)
async def preview_rename(
    payload: RenamePreviewRequest, session: Session = Depends(get_session)
) -> RenamePreviewOut:
    template = payload.template or get_rename_template(session)
    try:
        validate_template(template)
    except TemplateError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    stmt = select(MediaFile).where(MediaFile.is_video.is_(True))
    if payload.file_ids:
        stmt = stmt.where(MediaFile.id.in_(payload.file_ids))
    files = session.exec(stmt.order_by(MediaFile.id)).all()

    items = await build_preview(session, files, template)
    return RenamePreviewOut(
        items=items,
        ready=sum(1 for i in items if i.status == "ready"),
        conflicts=sum(1 for i in items if i.status == "conflict"),
        skipped=sum(1 for i in items if i.status == "skipped"),
        total=len(items),
        template=template,
    )


@router.post("/api/rename/execute", response_model=RenameExecuteOut)
async def execute_rename(
    payload: RenameExecuteRequest, session: Session = Depends(get_session)
) -> RenameExecuteOut:
    template = payload.template or get_rename_template(session)
    try:
        validate_template(template)
    except TemplateError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    files = await _select_files(session, payload.file_ids)
    if not files:
        raise HTTPException(status_code=404, detail="没有可执行的文件")
    preview = await build_preview(session, files, template)
    files_by_id = {f.id: f for f in files}

    selected: list[tuple[MediaFile, str]] = []
    used: dict[str, set[str]] = {}
    for item in preview:
        media = files_by_id.get(item.file_id)
        if not media or not item.new_name:
            continue
        parent = parent_of(media.source_ref)
        names = used.setdefault(parent, set())
        if item.status == "ready" and item.new_name not in names:
            selected.append((media, item.new_name))
            names.add(item.new_name)
        elif item.status == "conflict" and payload.conflict_policy == "suffix":
            datasource = get_datasource(session, media.source_type, media.openlist_id)
            candidate = await _unique_name(datasource, parent, item.new_name, names)
            if candidate:
                selected.append((media, candidate))
                names.add(candidate)

    if not selected:
        raise HTTPException(
            status_code=400,
            detail="没有可执行的文件，请先处理冲突或完成解析与匹配",
        )

    task_id = uuid4().hex
    task = TaskRecord(
        id=task_id,
        type="rename",
        source_type=selected[0][0].source_type,
        status="pending",
        total=len(selected),
        template=template,
        write_nfo=payload.write_nfo,
        download_posters=payload.download_posters,
    )
    session.add(task)
    for media, new_name in selected:
        session.add(
            TaskItem(
                task_id=task_id,
                file_id=media.id,
                name=media.original_name,
                new_name=new_name,
                status="pending",
            )
        )
    session.commit()
    task_manager.start(task_id)
    return RenameExecuteOut(task_id=task_id, total=len(selected))


async def _unique_name(datasource, parent: str, new_name: str, used: set[str]) -> str | None:
    stem, ext = os.path.splitext(new_name)
    for index in range(1, 50):
        candidate = f"{stem} ({index}){ext}"
        if candidate in used:
            continue
        if not await datasource.exists(parent, candidate):
            return candidate
    return None


@router.post("/api/rename/rollback", response_model=RollbackOut)
async def rollback_rename(
    payload: RollbackRequest, session: Session = Depends(get_session)
) -> RollbackOut:
    return await rollback_task(session, payload.task_id)
