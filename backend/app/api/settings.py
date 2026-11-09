import json
import os
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.core.renamer import TemplateError, validate_template
from app.core.strm import StrmTemplateError, validate_strm_template
from app.db import get_session
from app.models import OpenListInstance
from app.schemas import SettingsOut, SettingsUpdate
from app.services.crypto import encrypt
from app.services.settings import (
    get_allowed_paths,
    get_jellyfin_url,
    get_openlist_options,
    get_rename_template,
    get_strm_options,
    has_jellyfin_key,
    has_tmdb_key,
    set_value,
)

router = APIRouter(tags=["settings"])


def _to_out(session: Session) -> SettingsOut:
    options = get_openlist_options(session)
    strm = get_strm_options(session)
    return SettingsOut(
        rename_template=get_rename_template(session),
        allowed_paths=get_allowed_paths(session),
        has_tmdb_key=has_tmdb_key(session),
        openlist_concurrency=options["concurrency"],
        openlist_timeout=options["timeout"],
        openlist_retry=options["retry"],
        strm_url_template=strm["template"],
        strm_output_mode=strm["mode"],
        strm_target_dir=strm["target_dir"],
        strm_rules=strm["rules"],
        jellyfin_url=get_jellyfin_url(session),
        has_jellyfin_key=has_jellyfin_key(session),
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

    if payload.strm_url_template is not None:
        try:
            validate_strm_template(payload.strm_url_template)
        except StrmTemplateError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        set_value(session, "strm_url_template", payload.strm_url_template)

    if payload.strm_output_mode is not None:
        set_value(session, "strm_output_mode", payload.strm_output_mode)

    if payload.strm_target_dir is not None:
        cleaned = payload.strm_target_dir.strip()
        if cleaned and not os.path.isabs(cleaned):
            raise HTTPException(status_code=400, detail="STRM 目标目录必须是绝对路径")
        set_value(
            session, "strm_target_dir", os.path.normpath(cleaned) if cleaned else ""
        )

    if payload.strm_rules is not None:
        rules: list[dict] = []
        seen: set[str] = set()
        for rule in payload.strm_rules:
            source = os.path.normpath(rule.source.strip()).rstrip("/")
            if not source.startswith("/"):
                raise HTTPException(
                    status_code=400,
                    detail=f"源路径必须是以 / 开头的绝对路径：{rule.source}",
                )
            if source in seen:
                raise HTTPException(status_code=400, detail=f"源路径重复：{source}")
            target_dir = os.path.normpath(rule.target_dir.strip()).rstrip("/") or "/"
            if not target_dir.startswith("/"):
                raise HTTPException(
                    status_code=400,
                    detail=f"目标目录必须是以 / 开头的绝对路径：{rule.target_dir}",
                )
            if rule.target_type == "openlist":
                if not rule.target_id or not session.get(
                    OpenListInstance, rule.target_id
                ):
                    raise HTTPException(status_code=400, detail="请选择有效的 OpenList 实例")
                target_id = rule.target_id
            else:
                target_id = None
            seen.add(source)
            rules.append(
                {
                    "source": source,
                    "target_type": rule.target_type,
                    "target_id": target_id,
                    "target_dir": target_dir,
                }
            )
        set_value(session, "strm_rules", json.dumps(rules, ensure_ascii=False))

    if payload.jellyfin_url is not None:
        cleaned = payload.jellyfin_url.strip().rstrip("/")
        if cleaned:
            parsed = urlparse(cleaned)
            if parsed.scheme not in ("http", "https") or not parsed.netloc:
                raise HTTPException(
                    status_code=400, detail="Jellyfin 地址必须是合法的 http/https URL"
                )
        set_value(session, "jellyfin_url", cleaned)

    if payload.jellyfin_api_key:
        set_value(session, "jellyfin_api_key", encrypt(payload.jellyfin_api_key))

    session.commit()
    return _to_out(session)
