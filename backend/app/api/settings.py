import os

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.core.renamer import TemplateError, validate_template
from app.db import get_session
from app.schemas import SettingsOut, SettingsUpdate
from app.services.crypto import encrypt
from app.services.settings import (
    get_allowed_paths,
    get_openlist_options,
    get_rename_template,
    has_tmdb_key,
    set_value,
)

router = APIRouter(tags=["settings"])


def _to_out(session: Session) -> SettingsOut:
    options = get_openlist_options(session)
    return SettingsOut(
        rename_template=get_rename_template(session),
        allowed_paths=get_allowed_paths(session),
        has_tmdb_key=has_tmdb_key(session),
        openlist_concurrency=options["concurrency"],
        openlist_timeout=options["timeout"],
        openlist_retry=options["retry"],
    )


@router.get("/api/settings", response_model=SettingsOut)
def get_settings(session: Session = Depends(get_session)) -> SettingsOut:
    return _to_out(session)


@router.put("/api/settings", response_model=SettingsOut)
def update_settings(
    payload: SettingsUpdate, session: Session = Depends(get_session)
) -> SettingsOut:
    if payload.rename_template is not None:
        try:
            validate_template(payload.rename_template)
        except TemplateError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        set_value(session, "rename_template", payload.rename_template)

    if payload.allowed_paths is not None:
        roots: list[str] = []
        for path in payload.allowed_paths:
            cleaned = path.strip()
            if not cleaned:
                continue
            if not os.path.isabs(cleaned):
                raise HTTPException(status_code=400, detail=f"目录必须是绝对路径：{cleaned}")
            roots.append(os.path.normpath(cleaned))
        set_value(session, "allowed_paths", ";".join(roots))

    if payload.tmdb_api_key:
        set_value(session, "tmdb_api_key", encrypt(payload.tmdb_api_key))

    if payload.openlist_concurrency is not None:
        if not 1 <= payload.openlist_concurrency <= 10:
            raise HTTPException(status_code=400, detail="OpenList 并发数需在 1-10 之间")
        set_value(session, "openlist_concurrency", str(payload.openlist_concurrency))

    if payload.openlist_timeout is not None:
        if not 5 <= payload.openlist_timeout <= 300:
            raise HTTPException(status_code=400, detail="OpenList 超时需在 5-300 秒之间")
        set_value(session, "openlist_timeout", str(payload.openlist_timeout))

    if payload.openlist_retry is not None:
        if not 0 <= payload.openlist_retry <= 10:
            raise HTTPException(status_code=400, detail="OpenList 重试次数需在 0-10 之间")
        set_value(session, "openlist_retry", str(payload.openlist_retry))

    session.commit()
    return _to_out(session)
